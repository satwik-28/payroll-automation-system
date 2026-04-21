"""
TASK 18: Streaming Concepts — Real-time simulation
TASK 19: Kafka Producer-Consumer Pipeline
TASK 20: Kafka Advanced — Partitioning & Offsets
TASK 21: Structured Streaming — Real-time log processing
"""
import threading, queue, time, json, random, hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque
import sqlite3

BASE   = Path(__file__).parent
OUTPUT = BASE / "output"
OUTPUT.mkdir(exist_ok=True)
DB = Path(__file__).parent.parent / "shared/database/payroll.db"

# ══════════════════════════════════════════════════════════════
#  TASK 18: STREAMING CONCEPTS
# ══════════════════════════════════════════════════════════════
class StreamEvent:
    def __init__(self, event_type: str, payload: dict):
        self.event_type = event_type
        self.payload    = payload
        self.timestamp  = datetime.now().isoformat()
        self.event_id   = hashlib.md5(f"{event_type}{time.time()}".encode()).hexdigest()[:8]

    def to_dict(self):
        return {"event_id":self.event_id,"event_type":self.event_type,
                "payload":self.payload,"timestamp":self.timestamp}

class PayrollEventStream:
    """Simulates real-time event stream for payroll events."""
    EVENT_TYPES = ["PAYROLL_PROCESSED","EMPLOYEE_JOINED","SALARY_REVISED",
                   "LEAVE_APPLIED","ATTENDANCE_MARKED","LOAN_EMI_DUE","TDS_CALCULATED"]
    DEPTS = ["HR","IT","Finance","Sales","Ops","R&D"]

    def __init__(self, rate_per_second=2.0):
        self.rate = rate_per_second
        self._running = False
        self._stream: queue.Queue = queue.Queue(maxsize=1000)
        self.stats = {"produced": 0, "consumed": 0, "dropped": 0}

    def _gen_event(self) -> StreamEvent:
        et = random.choice(self.EVENT_TYPES)
        emp_id = random.randint(1, 30)
        payload = {
            "emp_id":     emp_id,
            "emp_code":   f"EMP{emp_id:03d}",
            "dept":       random.choice(self.DEPTS),
            "amount":     round(random.uniform(20000, 500000), 2),
            "period":     "April-2026",
        }
        if et == "ATTENDANCE_MARKED":
            payload["status"] = random.choice(["Present","Absent","Half-Day"])
            payload["check_in"] = "09:00"
        elif et == "LEAVE_APPLIED":
            payload["leave_type"] = random.choice(["CL","SL","PL"])
            payload["days"] = random.randint(1, 5)
        return StreamEvent(et, payload)

    def produce(self, duration_s=5.0):
        """Produce events for given duration."""
        end = time.time() + duration_s
        while time.time() < end and self._running:
            try:
                event = self._gen_event()
                self._stream.put_nowait(event)
                self.stats["produced"] += 1
            except queue.Full:
                self.stats["dropped"] += 1
            time.sleep(1.0 / self.rate)

    def consume(self, timeout=0.5):
        """Consume one event."""
        try:
            event = self._stream.get(timeout=timeout)
            self.stats["consumed"] += 1
            return event
        except queue.Empty:
            return None

    def run_streaming(self, duration_s=5.0):
        self._running = True
        consumed_events = []
        aggregates = defaultdict(lambda: {"count":0,"total_amount":0})

        producer = threading.Thread(target=self.produce, args=(duration_s,), daemon=True)
        producer.start()

        start = time.time()
        while time.time() - start < duration_s + 1:
            event = self.consume(timeout=0.2)
            if event:
                consumed_events.append(event.to_dict())
                agg = aggregates[event.event_type]
                agg["count"] += 1
                agg["total_amount"] += event.payload.get("amount", 0)

        self._running = False
        producer.join(timeout=2)
        return consumed_events, dict(aggregates)


# ══════════════════════════════════════════════════════════════
#  TASK 19: KAFKA SIMULATION
# ══════════════════════════════════════════════════════════════
class KafkaTopic:
    """Simulates a Kafka topic with partitions."""
    def __init__(self, name: str, num_partitions: int = 3, replication_factor: int = 2):
        self.name = name
        self.num_partitions = num_partitions
        self.replication_factor = replication_factor
        self._partitions = [[] for _ in range(num_partitions)]  # list of messages per partition
        self._offsets = [0] * num_partitions  # current offset per partition
        self.created_at = datetime.now().isoformat()

    def _get_partition(self, key=None) -> int:
        if key: return hash(key) % self.num_partitions
        return random.randint(0, self.num_partitions - 1)

    def info(self):
        return {
            "topic": self.name,
            "partitions": self.num_partitions,
            "replication": self.replication_factor,
            "messages": sum(len(p) for p in self._partitions),
            "total_offsets": self._offsets,
        }


class KafkaProducer:
    """Simulates Kafka producer."""
    def __init__(self, bootstrap_servers="localhost:9092"):
        self.bootstrap = bootstrap_servers
        self.sent = 0; self.failed = 0
        self.acks_mode = "all"  # strongest durability
        self._topics = {}

    def send(self, topic: KafkaTopic, value: dict, key: str = None):
        try:
            partition = topic._get_partition(key)
            offset    = topic._offsets[partition]
            message = {
                "offset":    offset,
                "partition": partition,
                "timestamp": datetime.now().isoformat(),
                "key":       key,
                "value":     value,
                "headers":   {"producer_id": "payroll_producer", "acks": self.acks_mode}
            }
            topic._partitions[partition].append(message)
            topic._offsets[partition] += 1
            self.sent += 1
            return {"topic": topic.name, "partition": partition, "offset": offset}
        except Exception as e:
            self.failed += 1; return {"error": str(e)}

    def flush(self):
        """Ensure all messages are delivered."""
        time.sleep(0.01)  # simulate network flush


class KafkaConsumer:
    """Simulates Kafka consumer with group management."""
    def __init__(self, group_id: str, auto_offset_reset="earliest"):
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.committed_offsets = {}  # partition → offset
        self.consumed = 0

    def subscribe(self, topics: list):
        self._topics = topics

    def poll(self, topic: KafkaTopic, partition: int = None, max_messages: int = 10):
        """Poll messages from topic."""
        results = []
        partitions = [partition] if partition is not None else range(topic.num_partitions)

        for p in partitions:
            committed = self.committed_offsets.get(f"{topic.name}:{p}", 0)
            messages  = topic._partitions[p][committed:committed + max_messages]
            for msg in messages:
                results.append(msg)
                self.consumed += 1

        return results

    def commit(self, topic: KafkaTopic, offsets: dict = None):
        """Commit offsets."""
        if offsets:
            for p, off in offsets.items():
                self.committed_offsets[f"{topic.name}:{p}"] = off
        else:
            for p in range(topic.num_partitions):
                self.committed_offsets[f"{topic.name}:{p}"] = topic._offsets[p]


# ══════════════════════════════════════════════════════════════
#  TASK 20: KAFKA ADVANCED — Partitioning & Offset Management
# ══════════════════════════════════════════════════════════════
class KafkaPartitionManager:
    """Manages partition assignment, rebalancing, offset tracking."""

    def __init__(self, topic: KafkaTopic, consumers: list):
        self.topic = topic
        self.consumers = consumers
        self._assignment = {}
        self._rebalance()

    def _rebalance(self):
        """Assign partitions evenly across consumers."""
        n_c = len(self.consumers)
        for i, p in enumerate(range(self.topic.num_partitions)):
            consumer = self.consumers[i % n_c]
            self._assignment.setdefault(consumer.group_id, []).append(p)
        print(f"  Rebalanced: {self._assignment}")

    def get_consumer_lag(self, topic: KafkaTopic) -> dict:
        """Calculate consumer lag per partition."""
        lags = {}
        for c in self.consumers:
            for p in range(topic.num_partitions):
                committed = c.committed_offsets.get(f"{topic.name}:{p}", 0)
                lag = topic._offsets[p] - committed
                lags[f"{c.group_id}:p{p}"] = {"committed": committed,
                                                "log_end": topic._offsets[p], "lag": lag}
        return lags

    def seek_to_offset(self, consumer: KafkaConsumer, topic: KafkaTopic, partition: int, offset: int):
        """Manual offset seek (for replay/recovery)."""
        consumer.committed_offsets[f"{topic.name}:{partition}"] = offset
        print(f"  Seeked {consumer.group_id} partition {partition} to offset {offset}")


# ══════════════════════════════════════════════════════════════
#  TASK 21: STRUCTURED STREAMING — Real-time log processing
# ══════════════════════════════════════════════════════════════
class StreamingWindow:
    """Tumbling window aggregation."""
    def __init__(self, window_size_s: int = 10):
        self.window_size = window_size_s
        self.windows = defaultdict(list)

    def add(self, event: dict, ts: float = None):
        ts = ts or time.time()
        window_key = int(ts // self.window_size) * self.window_size
        self.windows[window_key].append(event)

    def aggregate(self):
        results = []
        for window_ts, events in sorted(self.windows.items()):
            start = datetime.fromtimestamp(window_ts).strftime("%H:%M:%S")
            end   = datetime.fromtimestamp(window_ts + self.window_size).strftime("%H:%M:%S")
            by_type = defaultdict(int)
            total_amt = 0
            for e in events:
                by_type[e.get("event_type","UNKNOWN")] += 1
                total_amt += e.get("amount", 0)
            results.append({
                "window": f"{start}-{end}",
                "event_count": len(events),
                "event_breakdown": dict(by_type),
                "total_amount": round(total_amt, 2)
            })
        return results

class StructuredStreamingJob:
    """Simulates Spark Structured Streaming for real-time payroll logs."""

    def __init__(self, topic: KafkaTopic, consumer: KafkaConsumer):
        self.topic = topic; self.consumer = consumer
        self.micro_batches = []
        self.watermark_delay = 5  # seconds
        self.window = StreamingWindow(window_size_s=30)
        self.checkpoint = {"last_offset": {}}

    def process_micro_batch(self, batch_id: int, messages: list):
        """Process one micro-batch (like Spark streaming trigger interval)."""
        if not messages: return {"batch_id": batch_id, "processed": 0}

        # Transformations on micro-batch
        processed = []
        for msg in messages:
            val = msg["value"]
            processed.append({
                "event_type":  val.get("event_type",""),
                "dept":        val.get("dept",""),
                "amount":      val.get("amount", 0),
                "emp_id":      val.get("emp_id",""),
                "event_ts":    msg["timestamp"],
                "partition":   msg["partition"],
                "offset":      msg["offset"],
                "batch_id":    batch_id
            })
            self.window.add({**val,"event_type":val.get("event_type","")}, time.time())

        # Aggregation per dept in this micro-batch
        dept_agg = defaultdict(lambda: {"count":0,"total":0})
        for r in processed:
            dept_agg[r["dept"]]["count"] += 1
            dept_agg[r["dept"]]["total"] += r["amount"]

        result = {
            "batch_id": batch_id,
            "processed": len(processed),
            "dept_aggregation": {k: {"count":v["count"],"avg":round(v["total"]/v["count"],2)}
                                  for k,v in dept_agg.items()},
            "timestamp": datetime.now().isoformat()
        }
        self.micro_batches.append(result)

        # Update checkpoint
        for r in processed:
            p = r["partition"]
            self.checkpoint["last_offset"][f"p{p}"] = max(
                self.checkpoint["last_offset"].get(f"p{p}", 0), r["offset"])

        return result

    def run(self, n_batches: int = 3):
        """Run streaming job for n micro-batches."""
        print(f"  Streaming job started (trigger=1s, watermark={self.watermark_delay}s)")
        for i in range(1, n_batches + 1):
            messages = self.consumer.poll(self.topic, max_messages=5)
            result   = self.process_micro_batch(i, messages)
            print(f"  Micro-batch {i}: processed={result['processed']} events")
            for dept, agg in result.get("dept_aggregation",{}).items():
                print(f"    {dept}: count={agg['count']}, avg_amt=₹{agg['avg']:,.0f}")
            self.consumer.commit(self.topic)
            time.sleep(0.5)

        return self.micro_batches


def run():
    print("="*60)
    print("  TASK 18: Streaming Concepts")
    print("  TASK 19: Kafka Producer-Consumer")
    print("  TASK 20: Kafka Advanced (Partitioning + Offsets)")
    print("  TASK 21: Structured Streaming")
    print("="*60)

    # ── TASK 18 ───────────────────────────────────────────────
    print("\n══ TASK 18: REAL-TIME EVENT STREAM ══")
    stream = PayrollEventStream(rate_per_second=5.0)
    print("  Producing payroll events for 3 seconds...")
    events, agg = stream.run_streaming(duration_s=3.0)
    print(f"  Produced: {stream.stats['produced']} | Consumed: {stream.stats['consumed']} | Dropped: {stream.stats['dropped']}")
    print("  Event aggregation:")
    for etype, stats in agg.items():
        print(f"    {etype}: count={stats['count']}, total_amt=₹{stats['total_amount']:,.0f}")

    # ── TASK 19 ───────────────────────────────────────────────
    print("\n══ TASK 19: KAFKA PRODUCER-CONSUMER ══")

    # Setup topics
    payroll_topic   = KafkaTopic("payroll-events",    num_partitions=3, replication_factor=2)
    attendance_topic = KafkaTopic("attendance-events", num_partitions=2, replication_factor=2)

    producer = KafkaProducer("localhost:9092")
    consumer = KafkaConsumer("payroll-consumer-group")

    # Produce messages
    print("\n  Producing messages to Kafka topics:")
    payroll_events = [
        {"event_type":"PAYROLL_PROCESSED","emp_id":1,"period":"March-2026","net":62363},
        {"event_type":"PAYROLL_PROCESSED","emp_id":2,"period":"March-2026","net":172167},
        {"event_type":"SALARY_REVISED","emp_id":3,"old_basic":65000,"new_basic":70000},
        {"event_type":"TDS_CALCULATED","emp_id":4,"tds_amount":5000,"period":"March-2026"},
        {"event_type":"PAYROLL_PROCESSED","emp_id":5,"period":"March-2026","net":52949},
        {"event_type":"EMPLOYEE_JOINED","emp_id":31,"dept":"IT","basic":55000},
        {"event_type":"LOAN_EMI_DUE","emp_id":1,"emi":5000,"outstanding":65000},
        {"event_type":"PAYROLL_PROCESSED","emp_id":6,"period":"March-2026","net":35200},
    ]
    for evt in payroll_events:
        meta = producer.send(payroll_topic, evt, key=str(evt.get("emp_id","")))
        print(f"  → {evt['event_type']:<25} partition={meta['partition']} offset={meta['offset']}")
    producer.flush()

    print(f"\n  Topic info: {payroll_topic.info()}")

    # Consume messages
    print("\n  Consuming from all partitions:")
    msgs = consumer.poll(payroll_topic, max_messages=10)
    for msg in msgs:
        print(f"  ← P{msg['partition']}:O{msg['offset']}: {msg['value']['event_type']}")
    consumer.commit(payroll_topic)

    # ── TASK 20 ───────────────────────────────────────────────
    print("\n══ TASK 20: KAFKA ADVANCED — Partitioning & Offsets ══")

    c1 = KafkaConsumer("payroll-group-1")
    c2 = KafkaConsumer("payroll-group-2")
    mgr = KafkaPartitionManager(payroll_topic, [c1, c2])

    # Produce more
    for i in range(5):
        producer.send(payroll_topic, {"event_type":"ATTENDANCE_MARKED","emp_id":i+1}, key=str(i))
    c1.poll(payroll_topic, partition=0, max_messages=3)
    c1.commit(payroll_topic)

    print("\n  Consumer Lag Analysis:")
    lags = mgr.get_consumer_lag(payroll_topic)
    for key, info in lags.items():
        lag_status = "⚠ LAG" if info["lag"] > 2 else "✓ OK"
        print(f"  {key}: committed={info['committed']} | end={info['log_end']} | lag={info['lag']} {lag_status}")

    print("\n  Offset Seek (replay from offset 2, partition 0):")
    mgr.seek_to_offset(c1, payroll_topic, 0, 2)
    replayed = c1.poll(payroll_topic, partition=0, max_messages=3)
    print(f"  Replayed {len(replayed)} messages from offset 2")

    # ── TASK 21 ───────────────────────────────────────────────
    print("\n══ TASK 21: STRUCTURED STREAMING ══")
    log_topic = KafkaTopic("payroll-logs", num_partitions=2)
    log_producer = KafkaProducer()
    log_consumer = KafkaConsumer("streaming-group")

    log_events = [
        {"event_type":"PAYROLL_RUN","dept":"HR","amount":299650},
        {"event_type":"PAYROLL_RUN","dept":"IT","amount":1276234},
        {"event_type":"PAYROLL_RUN","dept":"Finance","amount":712547},
        {"event_type":"ERROR","dept":"Support","amount":0,"error":"Missing attendance"},
        {"event_type":"PAYROLL_RUN","dept":"Sales","amount":408941},
        {"event_type":"LOAN_DEDUCTION","dept":"HR","amount":5000},
        {"event_type":"TDS_FILED","dept":"ALL","amount":749419},
        {"event_type":"PAYROLL_RUN","dept":"R&D","amount":724335},
        {"event_type":"PAYROLL_RUN","dept":"Ops","amount":417202},
        {"event_type":"AUDIT_LOG","dept":"ALL","amount":0},
    ]
    for evt in log_events:
        log_producer.send(log_topic, evt, key=evt["dept"])

    streaming_job = StructuredStreamingJob(log_topic, log_consumer)
    batches = streaming_job.run(n_batches=3)

    print("\n  Window Aggregations:")
    for w in streaming_job.window.aggregate():
        print(f"  Window {w['window']}: {w['event_count']} events, total=₹{w['total_amount']:,.0f}")

    print(f"\n  Checkpoint state: {streaming_job.checkpoint}")

    # Save results
    results = {
        "task18_stream": {"produced":stream.stats["produced"],"consumed":stream.stats["consumed"],"event_types":list(agg.keys())},
        "task19_kafka": {"produced":producer.sent,"consumed":consumer.consumed,"topic_info":payroll_topic.info()},
        "task20_offsets": lags,
        "task21_streaming": batches,
        "timestamp": datetime.now().isoformat()
    }
    (OUTPUT/"streaming_results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\n✓ Results saved: {OUTPUT}/streaming_results.json")
    return results

if __name__ == "__main__":
    run()
