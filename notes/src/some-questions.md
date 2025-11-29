# Some Key Questions about PoV Generation Strategy

This document addresses key questions about how LLM and fuzzing work together in this CRS for PoV (Proof of Vulnerability) generation.

## 1. LLM's Primary Task

### Core Conclusion

**LLM is used for coverage-enhanced seed generation, NOT direct vulnerability finding.**

The LLM generates Python scripts (input generators) that produce fuzzing seeds. Vulnerability discovery relies entirely on: **high-coverage seeds → Fuzzer mutation → Sanitizer crash detection**.

### Evidence from Prompts

#### Evidence 1: GLANCE Agent Initial Prompt

[agents/glance.py#L12](https://github.com/Team-Atlanta/42-afc-crs/blob/main/components/seedgen/seedgen2/agents/glance.py#L12):

```python
PROMPT_GENERATE_FIRST_SCRIPT = """
Given the source code of a fuzzing harness, analyze the harness and generate a Python
script that can be used to generate valid testcases for the given harness.

Try your best to ensure the generated testcases cover as much harness code as possible.

The generated test cases should be diverse and effective for security testing purposes...
"""
```

Key indicators:
- "cover as much harness code as possible" → **Coverage goal**
- "diverse and effective" → Diversity focus
- "potential vulnerabilities" is mentioned but not the primary task

#### Evidence 2: COVERAGE Agent - Direct Coverage Optimization

[agents/coverage.py#L13](https://github.com/Team-Atlanta/42-afc-crs/blob/main/components/seedgen/seedgen2/agents/coverage.py#L13):

```python
PROMPT_CHECK_COVERAGE = """
I'm giving you the source code of a fuzzing harness function, and the its uncovered
region from the coverage report that I currently have for it using my set of input seeds.

Please help me determine whether all important pieces of code are covered...

These are the current uncovered regions:
{uncovered_code}
"""
```

This prompt clearly shows:
- LLM receives **real coverage reports** (`uncovered_code`)
- Task is to **analyze uncovered regions**
- Goal is **coverage improvement**, not vulnerability finding

#### Evidence 3: PREDICATES Agent - Branch Coverage

[agents/predicates.py#L16](https://github.com/Team-Atlanta/42-afc-crs/blob/main/components/seedgen/seedgen2/agents/predicates.py#L16):

```python
PROMPT_flip_predicate = """
Help me modify the python script that generates test cases.
I noticed that the current script does not generate test cases that cover a certain predicate.

The predicate is: `{predicate}`, which value is always `{predicate_value}`...

I want to flip the predicate value so we can cover more branches.
"""
```

This is explicitly **branch coverage optimization**: flipping condition values to cover more code paths.

### Summary: What LLM Does vs. Doesn't Do

| Task | Evidence | Involves Vulnerability Analysis? |
|------|----------|----------------------------------|
| Generate Python scripts for seeds | GLANCE prompt | No |
| Analyze uncovered code regions | COVERAGE prompt | No |
| Optimize scripts for coverage | MAXIMIZE_COVERAGE prompt | No |
| Flip branch conditions | PREDICATES prompt | No |
| Understand input format structure | MCPBOT prompt | No |

**LLM is never asked to:**
- Directly analyze code for vulnerabilities
- Generate exploits/PoVs
- Locate potential vulnerability points

---

## 2. How LLM-Generated Seeds Reach Fuzzers

### Overview

LLM generates **input generator scripts** (not seeds directly). Each script execution produces one seed with randomness, typically executed 100 times to produce 100 diverse seeds.

### Storage Pipeline (Sequential)

[task_handler.py#L255-284](https://github.com/Team-Atlanta/42-afc-crs/blob/main/components/seedgen/task_handler.py#L255):

```
Step 1: Pack seeds into tar.gz
    ↓
Step 2: Write record to Database (seeds table)
    ↓
Step 3: Send to cmin_queue (non-Java only)
```

### Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SeedGen (LLM Generation)                             │
│                                                                              │
│   Generator Script ─(execute 100x)─→ 100 seeds ─(pack)─→ seedmini_xxx.tar.gz │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
              ┌─────────────┐              ┌──────────────┐
              │  Database   │              │  cmin_queue  │ (non-Java only)
              │ (seeds表)   │              │  (RabbitMQ)  │
              └──────┬──────┘              └──────┬───────┘
                     │                            │
                     │                            ▼
                     │                     ┌──────────────┐
                     │                     │    CMIN++    │
                     │                     │   Service    │
                     │                     └──────┬───────┘
                     │                            │
                     │                            ▼
                     │                     ┌──────────────────┐
                     │                     │      Redis       │
                     │                     │ cmin:{task}:     │
                     │                     │    {harness}     │
                     │                     └────────┬─────────┘
                     │                              │
        ┌────────────┼──────────────────────────────┼────────────────┐
        ▼            │                              ▼                │
┌───────────────────────────────┐          ┌───────────┐    ┌───────────┐
│       PrimeFuzz               │          │ BandFuzz  │    │ Directed  │
│ (Direct DB + Fork new fuzzer) │          │           │    │           │
└───────────────────────────────┘          └───────────┘    └───────────┘
```

### How Each Fuzzer Consumes Seeds

| Fuzzer | Seed Source | Retrieval Method | Code Location |
|--------|-------------|------------------|---------------|
| **PrimeFuzz** | Database `seeds` table | Poll DB every 60s, query `fuzzer=seedmini` | [db_manager.py#L539-565](https://github.com/Team-Atlanta/42-afc-crs/blob/main/components/primefuzz/db/db_manager.py#L539) |
| **BandFuzz** | Redis `cmin:{task}:{harness}` | Fetch from CMIN results at epoch start | [cmin.go#L38-72](https://github.com/Team-Atlanta/42-afc-crs/blob/main/components/bandfuzz/internal/corpus/cmin.go#L38) |
| **Directed** | Redis `cmin:{task}:{harness}` | Poll every 10 minutes | [seed_syncer.py#L72](https://github.com/Team-Atlanta/42-afc-crs/blob/main/components/directed/src/daemon/modules/seed_syncer.py#L72) |

### Java Seeds Limitation

Java projects have `send_to_cmin=False` ([aixcc.py#L415](https://github.com/Team-Atlanta/42-afc-crs/blob/main/components/seedgen/infra/aixcc.py#L415)), meaning:
- Java seeds only go to Database
- Only PrimeFuzz can consume Java seedgen seeds
- BandFuzz/Directed cannot access Java seedgen seeds (they read from Redis CMIN)

---

## 3. Fuzzer Resource Scheduling and Seed Sharing

### Resource Allocation per Fuzzer

| Fuzzer | K8s Resource | Cores | Deployment Type |
|--------|-------------|-------|-----------------|
| **SeedGen** | 15 cores | Temporary, scales to 0 when idle | KEDA ScaledObject |
| **PrimeFuzz** | 16 cores | Static Deployment + DinD | Deployment |
| **BandFuzz** | 28 cores | Static Deployment | Deployment |
| **Directed** | Dynamic | Per-task | ScaledJob |

### Running Duration

| Fuzzer | Running Mode | Duration | Termination Condition |
|--------|-------------|----------|----------------------|
| **BandFuzz** | Epoch-based | 10-15 min/epoch | Auto-stop, select new fuzzlet |
| **PrimeFuzz** | Continuous | Unlimited | Cancel message or `canceled` status |
| **Directed** | Continuous | Unlimited | Cancel message or `canceled` status |

### Resource Adjustment on New Seeds

| Fuzzer | Resource Adjustment on New Seeds | Increases Resources? |
|--------|----------------------------------|---------------------|
| **BandFuzz** | No adjustment, uses new seeds at next epoch start | No |
| **PrimeFuzz** | **Forks new Docker container**, consumes extra 2 cores | **Yes** |
| **Directed** | No adjustment, background sync to running AFL++ | No |

#### PrimeFuzz Fork Behavior

[fuzzing_runner.py#L802-812](https://github.com/Team-Atlanta/42-afc-crs/blob/main/components/primefuzz/modules/fuzzing_runner.py#L802):

```python
if num_seeds_seedgen > 0:
    seed_corpus_dir = corpus_proj_dir / "seedgen" / harness_name
    # Launch NEW fuzzer process (additional resources!)
    asyncio.create_task(
        self.run_single_fuzzer(
            target=harness_name,
            corpus_dir=seed_corpus_dir,  # Uses seedgen corpus
            ...
        )
    )
```

Each fuzzer instance uses `fork=2` (2 cores), so forking a new instance adds 2 cores consumption.

### Seed Sharing Between Internal Instances

| Fuzzer | Internal Seed Sharing | Mechanism |
|--------|----------------------|-----------|
| **PrimeFuzz** | **No sharing** | Each Docker container has independent corpus |
| **Directed** | **No sharing** | Each harness runs independently |
| **BandFuzz** | **Yes, sharing** | Epoch end → upload seeds to CMIN → next epoch fetches updated corpus |

#### BandFuzz Sharing Flow

```
Epoch 1: Fuzzlet A (ASAN)
┌─────────────────┐
│ AFL++ runs 15min│ → discovers new seeds → uploads to cmin_queue
└─────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           CMIN Service                   │
│  (corpus minimization + store to Redis)  │
└─────────────────────────────────────────┘
         │
         ▼
Epoch 2: Fuzzlet B (UBSAN)
┌─────────────────┐
│ Fetches latest  │ ← pulls CMIN corpus (includes Epoch 1 discoveries)
│ corpus at start │
└─────────────────┘
         │
         ▼
Epoch 3: Fuzzlet A (ASAN) - rotates back
┌─────────────────┐
│ Gets corpus with│ ← now includes discoveries from Epoch 1 + 2
│ all discoveries │
└─────────────────┘
```

Code references:
- Upload seeds: [seeds.go#L187-211](https://github.com/Team-Atlanta/42-afc-crs/blob/main/components/bandfuzz/internal/seeds/seeds.go#L187)
- Fetch corpus: [grab.go#L43-54](https://github.com/Team-Atlanta/42-afc-crs/blob/main/components/bandfuzz/internal/corpus/grab.go#L43)

### Summary Diagram

```
                    New Seeds Arrive
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │BandFuzz │    │PrimeFuzz │    │ Directed │
    └────┬────┘    └────┬─────┘    └────┬─────┘
         │              │               │
         ▼              ▼               ▼
    Wait for       Fork new         Background
    epoch end,     Docker,          sync to
    use at start   ┌─────────┐      running
         │         │NewFuzzer│      AFL++
         │         │ +2cores │          │
         ▼         └─────────┘          ▼
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │Fixed    │    │Resources │    │Fixed     │
    │28 cores │    │increase  │    │resources │
    │+ sharing│    │no sharing│    │no sharing│
    └─────────┘    └──────────┘    └──────────┘
```
