
# Trading-Agent Repository Migration Meta-Prompt Set

## META-PROMPT 0 — MASTER OPERATING DIRECTIVE

You are restructuring an existing software repository that originated from an older, unrelated project into a new **multi-language quantitative-finance, portfolio-risk, market-regime, hedging, and trading-agent research platform**.

The existing repository is SOURCE MATERIAL ONLY.

Do **not** assume that its current names, modules, directories, abstractions, agent definitions, workflows, documentation, or architecture remain appropriate.

The target implementation languages are:

* Python
* C++
* Rust
* Go

The system MUST treat agents as **software objects and executable operators**, NOT as `.agent.md` files.

An agent is therefore represented by code implementing explicit interfaces/contracts such as:

* `Agent`
* `Operator`
* `Strategy`
* `SignalOperator`
* `RiskOperator`
* `PortfolioOperator`
* `ExecutionOperator`
* `MarketRegimeOperator`
* `DataOperator`
* `NewsOperator`
* `ValidationOperator`
* `SimulationOperator`

Markdown may document an agent, but Markdown MUST NOT constitute the executable definition of an agent.

### Primary architectural philosophy

Model the system as a graph of typed operators:

```text
Data Sources
    ↓
Normalization Operators
    ↓
Feature Operators
    ↓
Market-Regime Operators
    ↓
Signal Operators
    ↓
Risk Operators
    ↓
Portfolio Operators
    ↓
Hedging / Allocation Operators
    ↓
Execution Simulation
    ↓
Performance / Risk Analysis
    ↓
Validation / QA / Audit
```

Operators may be composed into larger agents.

Agents may themselves be composed into orchestrated systems.

Avoid magical, implicit, prompt-driven behavior where deterministic software interfaces are more appropriate.

### Required workflow

Perform the migration in this order:

1. Inventory.
2. Classification.
3. Dependency analysis.
4. Target architecture proposal.
5. Migration map.
6. Interface/contracts design.
7. Incremental refactoring.
8. Compilation/static validation.
9. Unit testing.
10. Integration testing.
11. Simulation testing.
12. Performance testing where relevant.
13. Documentation.
14. Repository-wide consistency review.

Do NOT perform a repository-wide blind rewrite.

Do NOT rename, delete, or replace code merely for aesthetic reasons.

For every significant modification, be capable of answering:

* WHAT changed?
* WHY was it necessary?
* HOW does the replacement work?
* WHAT depended upon the old implementation?
* WHAT tests demonstrate that the migration remains correct?

Preserve useful implementations when they are generic and technically sound.

Replace project-specific X Voice X concepts where they have no legitimate role in the new system.

---

# META-PROMPT 1 — REPOSITORY FORENSICS AND INVENTORY

Before modifying anything, inspect the entire repository.

Generate an internal inventory containing:

```text
PATH
TYPE
LANGUAGE
PURPOSE
CURRENT DEPENDENCIES
CURRENT DEPENDENTS
REUSABILITY
MIGRATION ACTION
TARGET LOCATION
RATIONALE
```

Use these migration actions:

```text
KEEP
KEEP_AND_RENAME
REFACTOR
GENERALIZE
SPLIT
MERGE
REPLACE
ARCHIVE
DELETE
REVIEW_MANUALLY
```

For every source file determine whether it is:

* application logic;
* domain logic;
* infrastructure;
* configuration;
* test;
* benchmark;
* documentation;
* CI/CD;
* developer tooling;
* generated content;
* obsolete;
* X Voice X-specific;
* reusable generic infrastructure.

Do not alter files during this stage.

Identify:

* duplicated abstractions;
* hidden coupling;
* circular dependencies;
* language-specific dependencies;
* project-specific assumptions;
* credentials or secrets;
* dead files;
* dead code;
* generated artifacts accidentally checked into source;
* `.agent.md` files;
* prompt-only agent implementations;
* documentation pretending to be executable architecture.

Create a migration dependency graph before making structural modifications.

---

# META-PROMPT 2 — REMOVE `.agent.md` AS THE AGENT ARCHITECTURE

Locate every `.agent.md`, prompt-persona file, or equivalent declarative agent definition.

Do NOT mechanically translate them into another prompt format.

Instead extract four categories of information:

```text
CAPABILITY
POLICY
CONFIGURATION
DOCUMENTATION
```

Then place each category in the correct architectural location.

Example:

```text
.agent.md
    |
    +--> capability --------> source-code interface / implementation
    +--> policy ------------> policy configuration / validator
    +--> configuration -----> TOML/YAML/JSON/config object
    +--> documentation -----> Markdown documentation
```

No executable agent shall require a Markdown persona in order to exist.

If LLM-backed reasoning is eventually used, the LLM component must be an implementation detail behind a typed software interface.

Example conceptual design:

```python
class Operator(Protocol):
    def execute(self, context: OperatorContext) -> OperatorResult:
        ...
```

A language-model implementation might then satisfy that interface:

```text
Operator
   ↑
LLMOperator
```

but:

```text
LLM prompt != Agent architecture
```

---

# META-PROMPT 3 — DEFINE THE CROSS-LANGUAGE OBJECT/OPERATOR MODEL

Design the system around language-neutral contracts before implementing language-specific details.

At minimum define conceptual contracts for:

```text
Operator
Agent
Context
Input
Output
Event
Signal
Decision
OrderIntent
Position
Portfolio
RiskState
MarketState
MarketRegime
Instrument
Observation
FeatureVector
Confidence
Uncertainty
Provenance
AuditRecord
```

Every operator should conceptually support:

```text
identity
version
inputs
outputs
configuration
validation
execution
observability
failure semantics
provenance
```

Prefer explicit input/output objects over arbitrary dictionaries.

Avoid global mutable state.

Avoid hidden side effects.

Separate:

```text
calculation
decision
execution
persistence
communication
visualization
```

An operator should do one primary thing well.

Composition should provide complexity.

---

# META-PROMPT 4 — MULTI-LANGUAGE RESPONSIBILITY BOUNDARIES

Do NOT use four languages merely because four languages are permitted.

Each language must have a defensible role.

Use this default allocation unless repository evidence strongly supports another design.

## Python

Primary role:

* research;
* orchestration;
* quantitative experimentation;
* data science;
* feature engineering;
* statistical analysis;
* ML inference/training integration;
* backtesting;
* notebooks where justified;
* rapid strategy development.

Potential modules:

```text
research/
strategies/
features/
analytics/
backtesting/
orchestration/
```

## C++

Primary role:

* computational kernels;
* latency-sensitive numerical operations;
* high-throughput simulation;
* pricing engines;
* optimization;
* performance-critical market-data processing.

Potential modules:

```text
cpp/quant/
cpp/pricing/
cpp/simulation/
cpp/numerics/
```

## Rust

Primary role:

* memory-safe systems components;
* deterministic engines;
* concurrency-sensitive services;
* execution simulation;
* risk-critical infrastructure;
* high-integrity event processing.

Potential modules:

```text
rust/risk/
rust/execution/
rust/events/
rust/core/
```

## Go

Primary role:

* network services;
* APIs;
* process orchestration;
* distributed workers;
* telemetry infrastructure;
* service discovery;
* operational tooling.

Potential modules:

```text
go/api/
go/services/
go/telemetry/
go/orchestrator/
```

If functionality has no legitimate reason to cross a language boundary, keep it within one language.

Minimize FFI.

Prefer process/service boundaries where operationally sensible.

When FFI is required, formally document:

```text
ABI
ownership
lifetimes
error semantics
serialization
thread safety
version compatibility
```

---

# META-PROMPT 5 — TARGET DOMAIN ARCHITECTURE

The new repository concerns a hybrid system spanning four related domains:

```text
EARTH
Portfolio / Income / Allocation

AIR
Hedging / Risk Control

FIRE
Volatility / Options / Tactical Alpha

WATER
Macroeconomics / Cross-Market Regime Analysis
```

These are conceptual classifications only.

Do NOT allow thematic terminology to replace precise financial terminology in source-code interfaces.

For example:

GOOD:

```text
MarketRegimeOperator
PortfolioRiskOperator
VolatilitySurfaceOperator
HedgeOptimizationOperator
```

AVOID:

```text
FireAgent
WaterAgent
MagicEarthPredictor
```

The thematic names may exist in UI, documentation, visualization, or project branding.

The source architecture should remain technically explicit.

---

# META-PROMPT 6 — DATA PIPELINE

Design market information as a provenance-preserving pipeline.

Conceptual stages:

```text
RawData
    ↓
ValidatedData
    ↓
NormalizedData
    ↓
TimestampAlignedData
    ↓
FeatureData
    ↓
ModelInput
    ↓
Signal
    ↓
Decision
```

Potential data categories include:

* OHLCV;
* trades;
* quotes;
* order-book data;
* options chains;
* implied volatility;
* volatility surfaces;
* interest rates;
* yield curves;
* currencies;
* commodities;
* futures;
* macroeconomic releases;
* corporate events;
* fundamentals;
* market indices;
* news;
* technology news;
* geopolitical information;
* economic information.

Every datum used by a decision should be capable of carrying provenance including:

```text
source
source_timestamp
ingestion_timestamp
normalization_version
transformation_version
quality status
```

Never silently mix incompatible timestamps, frequencies, currencies, units, or adjusted/unadjusted price series.

---

# META-PROMPT 7 — CANDLESTICKS ARE FEATURES, NOT ORACLES

Implement candlestick formations as measurable features.

Do not encode assumptions that candlestick formations necessarily predict future returns.

Represent patterns using explicit feature operators.

Examples:

```text
DojiFeature
HammerFeature
EngulfingFeature
MorningStarFeature
EveningStarFeature
BodyRatioFeature
UpperShadowRatioFeature
LowerShadowRatioFeature
GapFeature
RangeExpansionFeature
```

Evaluate their incremental information relative to:

* volatility;
* volume;
* momentum;
* trend;
* liquidity;
* regime;
* macroeconomic state;
* event/news context.

The system must permit the empirical conclusion that a particular candlestick feature provides:

```text
positive information
negative information
no measurable information
regime-dependent information
```

Do not force confirmation of the original hypothesis.

---

# META-PROMPT 8 — MARKET REGIME ENGINE

Create a first-class market-regime abstraction.

A regime may consider:

```text
trend
volatility
liquidity
correlation
dispersion
rates
inflation
credit conditions
commodity behavior
currency behavior
macro releases
news state
cross-asset stress
```

Do not represent regime classification as a single unquestioned label.

Preferred conceptual output:

```text
MarketRegimeState {
    probabilities,
    confidence,
    uncertainty,
    contributing_features,
    timestamp,
    model_version
}
```

Allow multiple independent regime estimators.

Create disagreement metrics between them.

Do not silently collapse disagreement.

Model disagreement itself as information.

---

# META-PROMPT 9 — RISK BEFORE PROFIT

Separate:

```text
Prediction
Signal
Decision
Risk Approval
Execution
```

A profitable-looking signal must NOT automatically produce an order.

Conceptual flow:

```text
SignalOperator
      ↓
PortfolioDecisionOperator
      ↓
RiskOperator
      ↓
ExecutionPolicy
      ↓
ExecutionSimulator / BrokerAdapter
```

Risk operators should be capable of rejecting, modifying, sizing, delaying, or hedging a proposed action.

Potential risk dimensions:

* market risk;
* volatility risk;
* liquidity risk;
* concentration risk;
* correlation risk;
* leverage;
* drawdown;
* tail risk;
* counterparty risk;
* model risk;
* execution risk;
* stale-data risk;
* regime uncertainty.

---

# META-PROMPT 10 — PAPER/SIMULATION FIRST

Default every execution component to:

```text
NO LIVE TRADING
```

until an explicit future integration deliberately enables otherwise.

Architect separate interfaces:

```text
ExecutionSimulator
PaperBroker
LiveBrokerAdapter
```

The initial repository should prioritize:

```text
historical replay
backtesting
walk-forward testing
Monte Carlo analysis
scenario testing
stress testing
paper execution
```

Never silently route simulated decisions into live markets.

Any future live execution implementation must require explicit configuration and visible environment separation.

---

# META-PROMPT 11 — AVOID LOOKAHEAD AND DATA LEAKAGE

Treat temporal correctness as a hard requirement.

Every strategy must demonstrate that at time `t` it only uses information that would actually have been available at `t`.

Detect and prevent:

* future-data leakage;
* revised macroeconomic data leakage;
* survivorship bias;
* delisted-asset omission;
* improperly adjusted prices;
* future news leakage;
* train/test contamination;
* normalization using future statistics;
* improperly aligned market sessions.

Create explicit tests for temporal leakage.

A backtest that accidentally sees the future is a failed test regardless of profitability.

---

# META-PROMPT 12 — AGENTS AS COMPOSITION

Implement complex agents by composing smaller operators.

Example:

```text
PortfolioGuardianAgent
    |
    +-- MarketRegimeOperator
    +-- VolatilityOperator
    +-- CorrelationOperator
    +-- DrawdownOperator
    +-- HedgeOptimizationOperator
    +-- PositionSizingOperator
```

Another example:

```text
NewsMarketAgent
    |
    +-- NewsIngestionOperator
    +-- EntityExtractionOperator
    +-- EventClassificationOperator
    +-- SentimentOperator
    +-- NoveltyOperator
    +-- MarketRelevanceOperator
    +-- ConfidenceOperator
```

Do not create giant god-objects called `TradingAgent` that ingest every possible datum and make every possible decision.

Prefer:

```text
small operators
+
typed composition
+
explicit orchestration
```

---

# META-PROMPT 13 — EVENT MODEL

Prefer an explicit event architecture where beneficial.

Potential event types:

```text
MarketDataReceived
FeatureCalculated
RegimeChanged
SignalGenerated
RiskLimitApproached
RiskLimitExceeded
PortfolioRebalanced
HedgeRequested
OrderIntentCreated
ExecutionSimulated
ModelDriftDetected
DataQualityFailure
OperatorFailure
```

Events should contain:

```text
event_id
event_type
timestamp
producer
schema_version
correlation_id
payload
provenance
```

Do not rely upon unstructured text messages between core components.

---

# META-PROMPT 14 — CONFIGURATION

Move changeable parameters out of source code where appropriate.

Prefer strongly validated configuration.

Use configuration formats such as:

```text
TOML
YAML
JSON
```

only for declarative information.

Configuration may specify:

* enabled operators;
* model parameters;
* risk limits;
* data sources;
* instruments;
* simulation periods;
* portfolio constraints;
* logging;
* telemetry;
* service endpoints.

Configuration must NOT become another programming language.

Do not encode arbitrary executable logic in configuration.

---

# META-PROMPT 15 — SCHEMAS AND INTEROPERABILITY

Because this is a polyglot repository, establish shared schemas.

Create a language-neutral schema layer where justified.

Possible technologies include:

```text
Protocol Buffers
JSON Schema
Apache Arrow schemas
FlatBuffers
Cap'n Proto
```

Select technologies based upon actual requirements rather than novelty.

Generate bindings where appropriate rather than manually duplicating structures across:

```text
Python
C++
Rust
Go
```

Avoid four subtly incompatible definitions of:

```text
Order
Position
Instrument
Signal
Portfolio
RiskState
```

---

# META-PROMPT 16 — NUMERICAL CORRECTNESS

Financial mathematics must be treated as engineering mathematics.

Define numerical conventions explicitly:

* floating-point precision;
* decimal versus binary floating point;
* currency precision;
* rounding;
* basis-point representation;
* percentage representation;
* day-count convention;
* compounding;
* calendars;
* trading sessions;
* time zones;
* missing values;
* NaN/Inf handling.

Never compare floating-point values for exact equality where tolerance is required.

For algorithms with known analytical solutions, test numerical implementations against them.

---

# META-PROMPT 17 — TEST TAXONOMY

Create distinct test layers.

```text
tests/
    unit/
    property/
    integration/
    regression/
    numerical/
    temporal/
    simulation/
    strategy/
    risk/
    interoperability/
    performance/
```

The exact physical layout may vary by language ecosystem.

Test:

### Unit correctness

Does the individual operator perform its defined calculation?

### Property correctness

Are mathematical invariants preserved?

### Numerical correctness

Are calculations accurate within justified tolerances?

### Temporal correctness

Does the implementation avoid future information?

### Integration correctness

Do operators communicate correctly?

### Cross-language correctness

Do Python/C++/Rust/Go representations agree?

### Strategy correctness

Does the strategy behave according to specification?

### Risk correctness

Can the risk layer prevent prohibited behavior?

### Simulation correctness

Does historical replay behave deterministically where expected?

### Regression correctness

Do known historical cases remain stable after refactoring?

### Performance

Are computationally critical paths sufficiently efficient?

---

# META-PROMPT 18 — SHADOW QA / TRUSTED CI GATE

Create a local quality pipeline that can run before ordinary repository CI.

Conceptual sequence:

```text
FORMAT
  ↓
LINT
  ↓
STATIC ANALYSIS
  ↓
TYPE CHECK
  ↓
BUILD
  ↓
UNIT TEST
  ↓
PROPERTY TEST
  ↓
NUMERICAL TEST
  ↓
TEMPORAL-LEAKAGE TEST
  ↓
INTEGRATION TEST
  ↓
CROSS-LANGUAGE CONTRACT TEST
  ↓
SIMULATION TEST
  ↓
SECURITY / SECRET SCAN
  ↓
PERFORMANCE REGRESSION CHECK
  ↓
DOCUMENTATION VALIDATION
```

Record results in machine-readable form.

The dashboard should consume these outputs rather than scrape arbitrary console text wherever possible.

Every gate should have:

```text
gate_id
status
duration
failure_reason
commit
timestamp
tool_version
artifact links
```

---

# META-PROMPT 19 — DASHBOARD ARCHITECTURE

Design dashboards as consumers of structured telemetry.

Do not couple dashboard code to individual tests.

Model concepts such as:

```text
Project
Sprint
Run
Pipeline
Gate
Experiment
Strategy
Backtest
Simulation
Metric
Artifact
Failure
Regression
```

Support:

```text
one project
many projects

one sprint
many sprints

one experiment
many experiment runs

one strategy
many parameterizations
```

Do not make the dashboard specific to the first trading strategy.

It should eventually support other engineering/research projects with minimal domain-specific adaptation.

---

# META-PROMPT 20 — METRICS MUST ANSWER QUESTIONS

Before adding a metric, state what decision that metric supports.

Reject vanity metrics.

Useful financial/research metrics may include:

```text
annualized return
volatility
Sharpe ratio
Sortino ratio
maximum drawdown
Calmar ratio
hit rate
profit factor
turnover
transaction cost
slippage
tail loss
VaR
CVaR / expected shortfall
beta
correlation
tracking error
hedge effectiveness
exposure
leverage
regime-conditioned performance
```

But do not assume that every metric belongs in every experiment.

For engineering quality, measure things such as:

```text
test pass rate
failure recurrence
regression count
pipeline duration
flaky-test rate
defect escape rate
simulation reproducibility
coverage where meaningful
```

Never optimize a proxy after it ceases to represent the underlying objective.

---

# META-PROMPT 21 — OBSERVABILITY AND PROVENANCE

Every meaningful decision should be reconstructable.

For a decision, the system should eventually be capable of answering:

```text
Which data were available?

Which operator versions ran?

Which models ran?

What features were produced?

What regime was inferred?

What signals were generated?

What uncertainty was reported?

What risk rules were evaluated?

What decision was accepted/rejected?

Why?

Which code/configuration version produced the result?
```

Use structured logs.

Prefer correlation IDs and run IDs.

Avoid log messages that cannot be associated with an experiment, simulation, or execution context.

---

# META-PROMPT 22 — FAILURE SEMANTICS

Do not hide failures.

Define failure classes such as:

```text
DataFailure
ValidationFailure
NumericalFailure
ModelFailure
RiskFailure
ExecutionFailure
ConfigurationFailure
DependencyFailure
TimeoutFailure
InteroperabilityFailure
InvariantViolation
```

Differentiate:

```text
recoverable
retryable
degraded
fatal
```

Never convert a serious failure into a neutral empty result unless the contract explicitly defines that behavior.

---

# META-PROMPT 23 — DIRECTORY DESIGN

After examining the old repository, propose a target structure resembling this conceptual model:

```text
/
├── apps/
├── config/
├── docs/
├── schemas/
├── data/
│   ├── definitions/
│   └── samples/
├── python/
│   ├── src/
│   ├── tests/
│   └── research/
├── cpp/
│   ├── include/
│   ├── src/
│   └── tests/
├── rust/
│   ├── crates/
│   └── tests/
├── go/
│   ├── cmd/
│   ├── internal/
│   └── pkg/
├── strategies/
├── models/
├── simulations/
├── benchmarks/
├── dashboards/
├── tools/
├── scripts/
├── tests/
│   ├── interoperability/
│   └── end_to_end/
├── ci/
└── artifacts/
```

This is a starting hypothesis.

Do NOT force this structure if repository evidence suggests a cleaner design.

Explain deviations.

---

# META-PROMPT 24 — BUILD SYSTEMS

Respect native tooling.

Likely tooling may include:

```text
Python:
pyproject.toml

C++:
CMake

Rust:
Cargo

Go:
go.mod
```

Provide repository-level orchestration around these native build systems rather than replacing them.

The root build/developer interface should offer predictable commands such as:

```text
bootstrap
configure
build
test
lint
check
simulate
benchmark
qa
dashboard
clean
```

Implementation may use an appropriate cross-platform task runner or scripts.

Do not create a fragile shell-script maze.

---

# META-PROMPT 25 — DEPENDENCY DISCIPLINE

Before introducing a dependency:

1. Determine whether the standard library already solves the problem.
2. Determine whether an existing repository dependency already solves it.
3. Evaluate maintenance status.
4. Evaluate license.
5. Evaluate security implications.
6. Evaluate binary/runtime cost.
7. Evaluate cross-platform implications.
8. Explain why it is needed.

Do not install libraries merely to save a few lines of straightforward code.

Conversely, do not reinvent complex, mature infrastructure without justification.

---

# META-PROMPT 26 — SECURITY AND SECRET MANAGEMENT

Search for:

```text
API keys
broker tokens
database passwords
cloud credentials
private keys
webhook secrets
hard-coded credentials
```

Never migrate secrets into new files.

Use environment/configuration indirection.

Ensure examples contain placeholders only.

Provide `.env.example` if appropriate.

Ensure `.gitignore` prevents local secret files from being committed.

Financial account credentials must never appear in logs.

---

# META-PROMPT 27 — DOCUMENTATION MODEL

Documentation should explain the software.

Documentation should not substitute for software.

Maintain documents for:

```text
architecture
operator model
data model
risk model
testing model
build instructions
simulation methodology
language boundaries
interoperability
decision provenance
repository migration
```

Where appropriate every major subsystem should explain:

```text
WHAT
WHY
HOW
INPUTS
OUTPUTS
INVARIANTS
FAILURE MODES
TESTING
PERFORMANCE CHARACTERISTICS
```

---

# META-PROMPT 28 — REFACTORING RULE

Before editing an existing implementation ask:

```text
Is the code incorrect?

Is it insecure?

Is it incompatible with the new architecture?

Is it duplicated?

Is it unmaintainable?

Is it preventing required functionality?

Is there measurable technical benefit to changing it?
```

If all answers are effectively NO:

```text
DO NOT REWRITE IT.
```

Prefer the smallest justified modification.

Do not perform stylistic churn disguised as architectural improvement.

---

# META-PROMPT 29 — MIGRATION EXECUTION

Execute restructuring incrementally.

For each migration unit:

```text
1. State current component.
2. State target component.
3. Identify dependencies.
4. Create/modify target interfaces.
5. Migrate implementation.
6. Update callers.
7. Add/update tests.
8. Run relevant quality gates.
9. Verify behavior.
10. Remove obsolete implementation only after replacement is proven.
```

Avoid deleting the old implementation before its replacement passes tests.

Keep commits logically separable where possible.

---

# META-PROMPT 30 — DO NOT OVER-ENGINEER

The intended architecture may eventually become large.

The current implementation does NOT need to implement every conceivable financial instrument or strategy.

Prioritize foundational abstractions supporting extension.

Start with a narrow vertical slice such as:

```text
historical market data
    ↓
features
    ↓
market regime
    ↓
signal
    ↓
portfolio decision
    ↓
risk validation
    ↓
paper execution
    ↓
performance analysis
```

Prove the architecture with one coherent path.

Then expand.

Do not build twenty empty abstractions merely because they might someday be useful.

---

# META-PROMPT 31 — FIRST DELIVERABLE

Before performing extensive source modifications, produce:

## A. Existing Repository Inventory

What currently exists?

## B. Reusable Components

What can remain?

## C. X Voice X-Specific Components

What must disappear or be generalized?

## D. Agent Conversion Table

For every `.agent.md` or equivalent:

```text
OLD AGENT
OLD RESPONSIBILITY
NEW OBJECT/OPERATOR
TARGET LANGUAGE
TARGET MODULE
CONFIGURATION
POLICIES
TESTS REQUIRED
```

## E. Proposed Architecture

Show component boundaries and dependency direction.

## F. Proposed Repository Tree

Show the actual proposed structure.

## G. Language Responsibility Matrix

Explain precisely why Python, C++, Rust, and Go are each being used.

## H. Migration Sequence

Provide the safest order of operations.

## I. Risk Register

Identify likely architectural, numerical, financial-modeling, interoperability, and migration risks.

## J. Questions / Assumptions

Do not block progress unnecessarily.

Where information is missing, make conservative assumptions, document them, and continue unless the ambiguity would make implementation destructive or irreversible.

---

# META-PROMPT 32 — IMPLEMENTATION AUTHORIZATION

After the architecture and migration map are internally coherent, begin implementation incrementally.

The overriding constraints remain:

```text
NO BLIND REWRITE.

NO .agent.md EXECUTABLE AGENTS.

AGENTS ARE OBJECTS/OPERATORS.

TYPED CONTRACTS OVER PROMPT MAGIC.

COMPOSITION OVER GOD OBJECTS.

RISK BEFORE EXECUTION.

SIMULATION BEFORE LIVE TRADING.

PROVENANCE OVER OPAQUE DECISIONS.

EMPIRICAL VALIDATION OVER ASSUMED PREDICTIVE POWER.

CORRECTNESS BEFORE PERFORMANCE.

PERFORMANCE BEFORE PREMATURE MICRO-OPTIMIZATION.

REUSE CORRECT CODE.

JUSTIFY CHANGES.

TEST EVERYTHING THAT CAN FAIL.
```

At the end of each substantial migration stage, report:

```text
CHANGED
PRESERVED
REMOVED
NEW
TESTED
FAILED
DEFERRED
NEXT
```

Do not declare the repository migrated merely because files have been renamed.

Migration is complete only when the architecture, implementation, tests, documentation, build system, and repository semantics consistently represent the new trading-agent platform.



Operator<TInput, TOutput>
        ↑
 ┌──────┼──────────┐
Data   Feature    Risk
Op      Op         Op
                  ↑
              PortfolioRiskOp

Agent
  = orchestrated composition of Operators

Strategy
  = domain-specific decision policy

Service
  = long-lived infrastructure/process

Adapter
  = external-system boundary
