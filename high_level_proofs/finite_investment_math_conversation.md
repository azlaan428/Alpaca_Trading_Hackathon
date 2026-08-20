
Yesterday 11:10 PM
The Plan For The Alpaca

Hackathon is to show, that

With a diversified stream of

Income, and so on, even if one is

Limited to paper initial input of

One hundred thousand dollars, and even if the initial

Position is relatively weak, with the

Right set of diversification investment instruments,

Even if it is only a few small

Categories, and time-horizons, and

Limited diversification (until the big money arrives),

Then reinvest back into more stable and more higher-reward

Instruments, with the proper

Agents, can be the key to

Achieving the ‘winning’ condition of maximum profits,

Even if the initial investment options

Are limited by the input you can put into

It at anyone time.

And so, I may need a ‘short’ support paper later

On this initial condition, and the best

Options to ensure long-term success, even if

Short-term input is very limited.

Author(s): Caius Lysander

Yes. The interesting part of the Alpaca hackathon thesis is that $100,000 of paper capital is not primarily a test of whether the agents can discover one spectacular trade. It can instead test whether an agentic system can turn a constrained initial capital base into a progressively stronger portfolio through allocation, risk control, reinvestment, and changing time horizons.

I would formalize the central hypothesis roughly as:

Under a fixed and comparatively limited initial capital constraint, an agentic investment system can improve long-run risk-adjusted portfolio growth by dynamically allocating capital across imperfectly correlated strategies, reinvesting realized returns, and progressively expanding into additional investment instruments as capital and confidence increase.

That gives you something considerably more defensible than simply "maximize profit." Maximum raw profit can encourage absurd behaviour: 100% allocation to whichever asset happens to have the highest ex-post return wins the simulation. That's not particularly interesting AI.

Instead, your hackathon can have several competing objectives:

Capital preservation → diversification → compounding → controlled expansion → long-horizon growth.

For example, the initial fictional $100,000 might deliberately be constrained:

$35k — relatively stable/core allocation.
$20k — broad-market or diversified growth exposure.
$15k — shorter-horizon/opportunistic strategies.
$10k — alternative or higher-volatility strategies.
$10k — cash/liquidity reserve.
$10k — dynamically allocated by the agents.

Those numbers shouldn't be presented as actual investment advice; they're experimental parameters. The agents then have to justify movements between the buckets.

And this is where your agent-as-operator/object architecture becomes useful. You don't actually need one omniscient "trading AI." You could have a Capital Allocator, Risk Agent, Market/Regime Agent, Diversification Agent, Execution Agent, Reinvestment Agent, and Auditor/Critic. The allocator proposes; risk constrains; execution acts; the auditor asks afterward whether the action actually improved the portfolio.

The reinvestment mechanism is especially important to your thesis. Suppose the agents make $5,000. The question isn't merely "How do we make another $5,000?" It becomes:

Where does the marginal dollar now have the highest expected utility?

Maybe part goes into the stable portfolio, some expands an existing successful strategy, some enters an instrument that was previously inefficient because the position would have been too small, and some remains liquid. As capital increases, the feasible investment universe itself can change.

That produces a nice state-transition model:

$100k constrained portfolio
→ returns generated
→ returns evaluated against risk
→ capital reinvested
→ diversification capacity increases
→ strategy universe expands
→ portfolio becomes more resilient
→ compounding continues.

You can consequently test something much more interesting than final account value. Compare the agentic portfolio against baselines such as buy-and-hold, equal weighting, static diversified allocation, single-strategy optimization, and perhaps a deliberately greedy profit-maximizer.

Your winning condition could then be a composite objective along the lines of

J=αG−βD−γV+δS+ϵR

where G is portfolio growth, D maximum drawdown, V volatility, S some measure of survival/capital preservation, and R risk-adjusted return. You could additionally penalize excessive turnover, transaction costs, concentration, and pathological leverage.

That makes the experiment capable of producing the somewhat counterintuitive result you seem interested in:

The agent producing the largest short-term return does not necessarily win.

An agent making $100k → $160k before crashing to $70k could lose to one producing $100k → $135k with substantially smaller drawdowns and a portfolio positioned for continued compounding.

And your eventual short support paper practically writes itself around one research question:

Can intelligent diversification and recursive reinvestment compensate for constrained initial capital?

The conclusion needn't claim that diversification magically manufactures wealth. Rather, the hypothesis is that limited capital makes allocation quality more important, not less important. Agentic orchestration can potentially improve the use of scarce capital by continually deciding what should be protected, what should be reinvested, what risks are worth accepting, and when increasing capital makes previously unavailable strategies rational.

That is a considerably stronger hackathon story than "we built some agents that trade stocks." It becomes an experiment in autonomous capital allocation under resource constraints—which is a much broader and more interesting optimization problem.

Yes. That makes your position considerably clearer: you aren't anti-technical-analysis; you're against treating technical analysis as an oracle.

Candlesticks contain information about historical price behaviour and market participation. They can reveal momentum, reversals, volatility structure, support/resistance behaviour, and sometimes useful recurring patterns. But fundamentally,

P
t+1
	


≡f(P
t
	

,P
t−1
	

,…)

because tomorrow's price can be affected by information that simply does not exist in yesterday's candles.

A surprise central-bank announcement, earnings shock, war, regulatory decision, bankruptcy, acquisition, tariff, natural disaster, technological breakthrough, or viral news event can alter the information set almost instantaneously. No clever interpretation of yesterday's hammer candlestick could literally contain information about an unforeseen event tomorrow.

That fits your multi-agent concept particularly well because you can distinguish different information domains rather than asking one methodology to know everything:

X
t
	

={
	

price/volume,
technical structure,
fundamentals,
macroeconomics,
news/events,
volatility,
options information,
cross-asset relationships,
portfolio state}.
	

The system then estimates something closer to

P(R
t+h
	

∣X
t
	

)

rather than pretending it knows

P(R
t+h
	

∣candlesticks alone).

And even the larger information set doesn't eliminate uncertainty. It merely gives the system a better basis for reasoning about uncertainty.

That's where I think your engineering mentality is particularly visible. You're not really asking the agents to predict the future correctly. You're asking them to make defensible decisions given incomplete information about the future.

There's an important distinction:

Prediction: "The stock will rise tomorrow."

Decision under uncertainty: "Current evidence moderately favours appreciation, but event risk and volatility remain elevated; therefore take limited exposure, preserve liquidity, define the loss boundary, and reconsider if the information state changes."

The second is much closer to the architecture you've been describing.

News also needs exactly the skepticism you're applying to TA. News isn't "ground truth" either. It can be stale, sensationalized, incomplete, duplicated across outlets, already priced in, or interpreted differently by different market participants. So I'd make the News Agent produce evidence + provenance + confidence + novelty, rather than simply BULLISH/BEARISH.

Same with macroeconomics. A rate cut isn't mechanically bullish; markets might have already priced it in, or interpret the cut as evidence that economic conditions are deteriorating.

So your system becomes less:

TA + macro + news = prediction

and more:

TA + macro + fundamentals + news + volatility + options + portfolio state = evidence

then:

evidence → uncertainty estimation → competing hypotheses → risk assessment → capital allocation.

That last transformation is probably the intellectual core of your hackathon idea.

You're effectively saying: I don't need my agents to know what happens next. I need them to know that they don't know—and allocate capital intelligently anyway.

For an uncertainty-oriented quantitative system, that's a much more defensible objective than trying to build an electronic fortune teller out of candlesticks.

mine idea of bull/bear markets or rather bear-bull markets: [-1,1] normalization so agents can make a decision more effectively, whilst the master capital allocator assigns probability weights, doubt weights and uncertainty and a priori success/failures or confidence intervals of say (0,1] so we know how to distribute, manage, buy/sell and so on across the hackathon

That is a strong abstraction, especially for a multi-agent system, because it separates directional opinion from confidence in that opinion.

I would keep your two ideas as distinct channels:

s
i
	

∈[−1,1]

for the agent's directional market view, where −1 is maximally bearish, 0 is neutral/indeterminate, and +1 is maximally bullish.

Then separately:

c
i
	

∈(0,1],u
i
	

∈[0,1],d
i
	

∈[0,1]

for confidence, uncertainty, and doubt. I would not collapse those into one number too early, because they are not necessarily the same thing. An agent can have low confidence because evidence is weak, or high uncertainty because signals conflict, or high doubt because its own historical performance in the present regime has been poor.

Then each specialized agent could emit something like

A
i
	

=(s
i
	

,c
i
	

,u
i
	

,d
i
	

,p
i
+
	

,p
i
−
	

,Δt
i
	

,r
i
	

)

where p
i
+
	

 and p
i
−
	

 are estimated probabilities of favourable/unfavourable outcomes, Δt
i
	

 is the relevant time horizon, and r
i
	

 is the estimated risk or loss exposure.

That last part matters because a bullish signal with 80% confidence over the next fifteen minutes is not directly comparable to a moderately bullish signal with 65% confidence over six months.

The master allocator can then reason over the whole ensemble:

S=
∑
i
	

w
i
	

∑
i
	

w
i
	

s
i
	

c
i
	

(1−u
i
	

)(1−d
i
	

)
	

where w
i
	

 can include the historical reliability of agent i, current-regime relevance, instrument-specific expertise, and recent calibration quality.

But I would go one step further: don't let the allocator interpret S=0 as necessarily neutral.

There are two radically different ways to get zero:

(+0.9)+(−0.9)≈0

and

(+0.05)+(−0.05)≈0.

The first means violent disagreement. The second means nothing much is happening.

So your system should explicitly calculate something like disagreement:

D=
∑
i
	

w
i
	

∑
i
	

w
i
	

∣s
i
	

−S∣
	

High D should probably reduce capital deployment even if the aggregate score looks attractive.

That gives the allocator a richer state:

(S,C,U,D,R)
	

Directional score, ensemble confidence, uncertainty, disagreement, and portfolio risk.

Then your buy/sell logic can become continuous rather than categorical.

Instead of:

BUY / HOLD / SELL

you can have:

a∈[−1,1]

where perhaps:

−1: maximum permitted short/reduction
−0.4: moderate reduction
0: no position change
+0.3: small allocation
+1: maximum permitted long allocation

The allocator then turns that into actual capital subject to constraints:

x
j
	

=C
available
	

⋅f(S
j
	

,C
j
	

,U
j
	

,D
j
	

,R
j
	

)

while enforcing things such as

j
∑
	

x
j
	

≤C
deployable
	

,

sector/instrument limits, maximum drawdown targets, options exposure limits, cash reserve requirements, and hedge requirements.

Your a priori success/failure idea is also useful, but I'd phrase it as a prior rather than a fixed truth:

P(success∣A
i
	

,regime)

The system can then update it after every paper-trading episode:

P
t+1
	

∝P(new evidence∣agent/model)P
t
	

.

That effectively gives you a Bayesian reputation system for your agents. If the volatility agent performs particularly well during volatility expansions, its weight increases under similar future regimes. If a candlestick agent repeatedly fails during news-driven markets, its contribution can be reduced there.

The result is much more interesting than a collection of agents voting bull or bear.

You are building something closer to:

A probabilistic capital-allocation layer in which specialized agents express directional beliefs, confidence, uncertainty, disagreement, and regime-conditioned historical reliability, while a central allocator converts those beliefs into constrained portfolio actions.

And your [−1,1] normalization is valuable because it gives all of those heterogeneous agents a common decision interface without forcing them to use the same internal methodology. A macro agent, options agent, candlestick agent, volatility agent, and news agent can all speak very different analytical languages internally while ultimately emitting compatible standardized outputs.

That is exactly the kind of interface abstraction that makes a multi-agent system manageable.

now, summarize the main crux of mine mathematical conjecture for multi-agentic trading, portfolio, risk and options allocations

The crux of your mathematical conjecture is that multi-agentic quantitative trading should be formulated as constrained probabilistic capital allocation under uncertainty—not as maximum-profit prediction.

Each specialized agent A
i
	

—technical/candlestick, macroeconomic, news, volatility, hedging, risk, options, etc.—maps heterogeneous evidence into a common normalized representation:

s
i
	

∈[−1,1]

where −1 represents maximally bearish evidence, 0 indeterminate/neutral evidence, and +1 maximally bullish evidence.

But direction alone is insufficient. Each agent additionally supplies measures such as

c
i
	

∈(0,1],u
i
	

,d
i
	

∈[0,1],

representing confidence, uncertainty, and doubt, together with prior/historical success probabilities, relevant time horizon, expected risk, and potentially confidence intervals.

Thus an agent effectively produces

A
i
	

=(s
i
	

,c
i
	

,u
i
	

,d
i
	

,p
i
	

,Δt
i
	

,r
i
	

,…).

The Master Capital Allocator does not simply majority-vote these signals. It weights them according to confidence, uncertainty, historical calibration, market regime, time horizon, and relevance:

S=
∑
i
	

w
i
	

∑
i
	

w
i
	

s
i
	

c
i
	

(1−u
i
	

)(1−d
i
	

)
	

.

Critically, the system also measures agent disagreement because

(+0.9)+(−0.9)≈0

is fundamentally different from

(+0.05)+(−0.05)≈0.

The former represents substantial uncertainty or conflicting evidence; the latter represents genuine neutrality. Therefore disagreement itself becomes an allocation variable.

The allocator consequently reasons over a multidimensional state approximately of the form

X
t
	

=(S,C,U,D,R,H,V,O,Δt)
	

where S is directional evidence, C confidence, U uncertainty, D disagreement, R risk, H hedging requirements, V volatility/regime information, O options-related state, and Δt the relevant investment horizon.

Portfolio decisions then become a constrained optimization problem:

x
max
	

E[R(x)]−λ
R
	

R−λ
D
	

DD−λ
U
	

U−λ
C
	

C
concentration
	

−λ
T
	

T
cost
	

subject to

j
∑
	

x
j
	

≤C
deployable
	

,

along with liquidity, exposure, diversification, hedging, options, drawdown and capital-preservation constraints.

The key conjecture is therefore:

A heterogeneous multi-agent system that explicitly models direction, confidence, uncertainty, disagreement, risk and prior performance can allocate finite capital more robustly across trading, portfolio, hedging and options strategies than systems optimizing primarily for directional prediction or maximum terminal profit.

And importantly, success does not require maximum P&L.

A system producing

$100,000→$104,000

with small drawdowns, controlled volatility and substantial retained liquidity can represent a superior technical result to

$100,000→$125,000

obtained through enormous concentration and exposure to catastrophic loss.

So the deepest formulation of your conjecture is:

Optimal Agentic Trading

=max(Profit)
	

but rather

Optimal Agentic Trading=max(Risk-Adjusted Capital Utility∣Uncertainty, Constraints, Information)
	

with survival → preservation → intelligent allocation → controlled risk → compounding taking precedence over chasing the largest possible paper return.

That is the mathematical spine connecting your four hackathon domains—hedging, volatility, risk and options—into one coherent multi-agent capital-allocation problem.
