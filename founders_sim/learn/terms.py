"""The vocabulary curriculum: every term the game teaches, IN ORDER.

Order matters: each term builds on earlier ones (revenue -> burn ->
runway -> valuation -> dilution -> cap table ...). A term is unlocked the
first time the matching situation happens in play (see `notebook.learn`).

`example` is a template: {mrr}, {cash}, {runway} ... are replaced with the
player's own company numbers (see engine.example_vars).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Term:
    id: str
    name: str
    category: str       # startup | ai | metrics | gtm | vc | finance
    tier: int           # 1..6 curriculum stage
    definition: str
    why: str
    example: str
    related: list[str]
    needs: list[str]    # terms that should be learned first
    deeper: str = ""    # benchmarks, common mistakes, practice (see DEEPER below)


TIERS = {
    1: "Foundations: problems, customers, money in and out",
    2: "Building with AI agents",
    3: "Growth and unit economics",
    4: "Go-to-market, markets and competition",
    5: "Fundraising and ownership",
    6: "Corporate finance, debt and exits",
}

TERMS: dict[str, Term] = {}
_tier = 1


def T(id, name, category, definition, why, example, related="", needs=""):
    TERMS[id] = Term(id, name, category, _tier, definition, why, example,
                     related.split(), needs.split())


# ============================================================ TIER 1
T("startup", "Startup", "startup",
  "A young company searching for a repeatable, scalable business - not just a small business, but one designed to grow fast.",
  "The word 'searching' is the point: at first you don't know what customers want. Your job is to find out before the money runs out.",
  "{company} is a startup: one founder, {cash} in the bank, and a guess about what customers need.",
  "founder mvp runway")
T("founder", "Founder", "startup",
  "The person who starts the company and owns it at the beginning. A solo founder does everything: product, sales, finance.",
  "Your time and energy are the scarcest resources in the company. Burning out ends the company as surely as running out of cash.",
  "You own {founder_pct} of {company} and have about 50 working hours a week to spend.",
  "equity burnout", "startup")
T("problem", "Problem (customer pain)", "startup",
  "Something that costs a specific group of people time, money or nerves - badly enough that they would pay to make it go away.",
  "Startups rarely die from bad code. They die from building something nobody needs. Start from a painful problem, not from a cool solution.",
  "Your ideas in product/ideas.md are guesses about problems. Some are 'hair on fire' painful, some are only mildly annoying.",
  "customer_interview value_proposition", "startup")
T("customer_interview", "Customer interview", "startup",
  "A conversation with a potential customer about THEIR life and problems (not a sales pitch for your idea).",
  "It is the cheapest experiment there is: one hour of talking can save months of building the wrong thing. Ask about past behaviour ('when did this last happen?'), not opinions about the future.",
  "Each `interview` costs you a few hours and writes notes into customers/notes/ - read them, the gold is in the quotes.",
  "problem hidden_need wtp", "problem")
T("hidden_need", "Hidden need (customer insight)", "startup",
  "A need customers have that you could not have guessed from your desk - you only learn it by talking to them or watching them.",
  "Hidden needs are your edge: competitors who skip interviews never find them.",
  "Features that appear on your roadmap only after interviews are hidden needs you uncovered.",
  "customer_interview pmf", "customer_interview")
T("wtp", "Willingness to pay (WTP)", "startup",
  "The highest price a customer would accept for your product.",
  "Price above it and nobody buys; price far below it and you leave money on the table. It differs between customer groups.",
  "Interview notes hint at each person's WTP. Your price is {price} ({price_unit}).",
  "pricing customer_interview", "customer_interview")
T("validation", "Validation", "startup",
  "Collecting evidence that a problem is real and that people will pay for your solution, BEFORE building much.",
  "Evidence beats opinion. Strong signals: people describe the pain unprompted, already hack together workarounds, or pre-pay.",
  "After several interviews you `idea pick` the idea with the strongest evidence, instead of the one you like most.",
  "problem_solution_fit customer_interview", "customer_interview")
T("problem_solution_fit", "Problem/solution fit", "startup",
  "Evidence that your proposed solution actually solves a real, painful problem for a clear group of people.",
  "It is the first milestone. Without it, everything built later rests on sand.",
  "Picking the idea whose problem most interviewees really have gives {company} problem/solution fit.",
  "validation pmf mvp", "validation")
T("mvp", "MVP (minimum viable product)", "startup",
  "The smallest version of the product that delivers real value to a real customer, so you can start learning from usage.",
  "Shipping early is how you learn. An MVP is not a bad product - it is a small one that does one thing well.",
  "Your first merged feature makes {company}'s product live: that is your MVP.",
  "iteration problem_solution_fit", "problem_solution_fit")
T("iteration", "Iteration", "startup",
  "Repeating a build -> measure -> learn loop: ship something, watch what happens, adjust.",
  "Speed of iteration, not the brilliance of the first idea, is what separates startups that find their market from those that don't.",
  "Each week in the game is one turn of the loop: build with agents, look at `metrics`, decide what to change.",
  "mvp pivot", "mvp")
T("pivot", "Pivot", "startup",
  "A deliberate change of direction (customer, problem or solution) while keeping what you have learned.",
  "Pivoting early is cheap; pivoting after a year of building is expensive. That is why validation comes first.",
  "`idea pick` after you've already built means a pivot: you keep the code that still fits and lose some customers.",
  "iteration validation", "iteration")
T("revenue", "Revenue", "finance",
  "Money customers pay you for the product. Also called sales or 'the top line'.",
  "Revenue is the most honest form of validation: people vote with their wallets.",
  "{company} currently earns about {revenue_month} of revenue per month.",
  "profit mrr pricing")
T("pricing", "Pricing", "startup",
  "Deciding what you charge and how (per month, per user, per use, a cut of each transaction).",
  "Price changes profit faster than almost any other lever, and it signals who the product is for. Most first-time founders charge too little.",
  "Your price is {price} ({price_unit}); change it with `price <amount>` and watch signups and churn react.",
  "wtp revenue arpu", "revenue wtp")
T("costs", "Costs (expenses)", "finance",
  "Money the company spends: your living costs/salary, servers, AI compute, ads, people.",
  "Every dollar of cost shortens your runway unless it brings back more than a dollar.",
  "{company} spends about {costs_month} per month right now.",
  "burn_rate fixed_variable_costs", "revenue")
T("profit", "Profit", "finance",
  "Revenue minus costs. Positive = profit, negative = loss.",
  "A profitable company controls its own destiny: it needs nobody's permission (or money) to keep existing.",
  "This month: {revenue_month} revenue - {costs_month} costs = {profit_month}.",
  "revenue costs break_even", "costs")
T("cash", "Cash", "finance",
  "The money actually in your bank account right now.",
  "Companies don't die when they are unprofitable; they die when cash hits zero. 'Cash is oxygen.'",
  "{company} has {cash} in the bank.",
  "burn_rate runway")
T("burn_rate", "Burn rate", "finance",
  "How much cash the company loses per month. Gross burn = total spending; net burn = spending minus revenue.",
  "It is the speed at which you approach zero. Investors always ask for it.",
  "Net burn: {costs_month} costs - {revenue_month} revenue = {burn} per month.",
  "runway cash costs", "cash costs")
T("runway", "Runway", "finance",
  "How long until the cash runs out: cash divided by net monthly burn.",
  "It is your countdown clock. Fundraising takes 3-6 months, so below 6 months of runway you are already late.",
  "{cash} cash / {burn} monthly burn = {runway} of runway.",
  "burn_rate default_alive", "burn_rate")
T("bootstrapping", "Bootstrapping", "startup",
  "Building the company with your own savings and customer revenue instead of investor money.",
  "You keep 100% ownership and full control, but growth is limited by what customers pay you.",
  "So far {company} has raised {raised} from outside. With none raised, you are bootstrapping.",
  "ramen_profitable equity", "runway")
T("ramen_profitable", "Ramen profitable", "startup",
  "The company earns just enough to cover its costs including the founder's very basic living expenses.",
  "It removes the countdown clock: you can no longer die by default, which also makes you far stronger when negotiating with investors.",
  "You'd be ramen profitable when monthly revenue passes about {costs_month}.",
  "bootstrapping default_alive break_even", "profit bootstrapping")
T("burnout", "Burnout", "startup",
  "Physical and emotional exhaustion from sustained overwork.",
  "A solo founder IS the company. Rested founders make better decisions; exhausted ones make expensive mistakes.",
  "Your energy is {energy}/100. `rest` restores it; `crunch` trades it for extra hours.",
  "founder", "founder")

# ============================================================ TIER 2
_tier = 2
T("llm", "LLM (large language model)", "ai",
  "An AI model trained on huge amounts of text that predicts what comes next - which lets it write, summarise and produce code.",
  "It is the engine inside every coding agent. It is very capable but not a database of truth: it produces plausible text, which is usually - not always - correct.",
  "The `fast` and `smart` models you choose for `agent run` are LLMs of different size and price.",
  "agent hallucination token")
T("agent", "AI agent (coding agent)", "ai",
  "An LLM running in a loop with tools: it reads files, runs commands, edits code, checks the result and repeats until the task is done.",
  "Agents turn one founder into a small team - IF they are directed well. An agent is a fast, tireless junior colleague with no memory of your project.",
  "`agent run product/specs/<feature>.md` starts agents on a spec. They write to agents/runs/.",
  "llm spec agentic_loop human_in_the_loop", "llm")
T("tool_use", "Tool use (function calling)", "ai",
  "A model's ability to call tools - read a file, run a command, search, call an API - instead of only writing text. The model asks for the call; the agent program runs it and feeds the result back.",
  "Tools are what turn a chatbot into an agent. Every tool is also a risk: a tool that can delete or pay can delete or pay by mistake.",
  "{company}'s agents use tools to edit code and run tests - that is where tests.log comes from.",
  "agent agentic_loop guardrails mcp", "agent")
T("agentic_loop", "Agentic loop", "ai",
  "The cycle an agent repeats: gather context -> take an action (edit, run a command) -> check the result -> repeat.",
  "Understanding the loop tells you where to help: give it good context at the start and a way to check its own work (tests) at the end.",
  "Each run folder shows the loop's traces: report.md (what it did) and tests.log (how it checked).",
  "agent tests context", "agent")
T("prompt", "Prompt", "ai",
  "The instructions you give a model. For agents, the most important prompt is the task description.",
  "Output quality follows input quality. Vague prompt, vague result.",
  "The spec file you pass to `agent run` IS your prompt.",
  "spec context", "llm")
T("system_prompt", "System prompt", "ai",
  "Standing instructions a model receives before the user's message: its role, rules and style. Agent tools build one for every session.",
  "It shapes every answer without being repeated. Project memory files (AGENTS.md, CLAUDE.md) are loaded into it - that is why they work.",
  "Each of {company}'s agent runs starts from a system prompt plus your spec; the `memory` upgrade adds agents/AGENTS.md to it.",
  "prompt agents_md context", "prompt")
T("spec", "Spec (specification)", "ai",
  "A short written description of what to build: the goal, the context, the tasks, how to verify it, and what is out of scope.",
  "Agents do exactly what the words say, not what you meant. A clear spec is the highest-leverage hour in agentic development.",
  "`spec new <feature>` creates a template; `spec check <file>` scores it. Runs from weak specs produce more bugs.",
  "prompt acceptance_criteria task_decomposition context", "prompt agent")
T("context", "Context (and context window)", "ai",
  "Everything the model can 'see' while working: your instructions, the files it read, earlier output. The context window is the maximum amount it can hold.",
  "An agent knows nothing about your project except what is in its context. Too little -> it guesses. Too much irrelevant text -> it loses the thread.",
  "The '## Context' section of a spec should point to real files (e.g. customers/notes/maria.md) so the agent builds for real customers.",
  "token agents_md spec", "prompt")
T("rag", "RAG (retrieval-augmented generation)", "ai",
  "Looking up relevant documents first (in files, a database or a search index) and putting them into the model's context, so it answers from real sources rather than from memory.",
  "It is the standard cure for 'the model doesn't know our stuff': cheaper than retraining, easy to update, and it lets you show sources. Bad retrieval means confidently wrong answers.",
  "When your spec's Context points to customers/notes/maria.md you are doing RAG by hand: you retrieve the right document for the agent.",
  "context hallucination fine_tuning", "context")
T("token", "Token", "ai",
  "The unit models read and write in - roughly 3/4 of a word. Usage is billed per token.",
  "Tokens are your compute bill. Bigger models, more agents and more context all cost more tokens.",
  "{company} has spent {compute} on agent compute so far (see agents/usage.log).",
  "compute_budget model_tier context", "llm")
T("compute_budget", "Compute budget", "ai",
  "The money you allow yourself to spend on AI model usage.",
  "Agent work feels free but is a real cost line. Spend it where it pays: smart models for hard features, cheap ones for simple work.",
  "Every `agent run` reports its compute cost when it finishes and logs it to agents/usage.log (`cat agents/usage.log`). Bigger runs cost more: you pay for the work done.",
  "token model_tier costs", "token")
T("model_tier", "Model tier (fast vs. smart)", "ai",
  "Providers sell several model sizes: small ones are fast and cheap, large ones reason better but cost more.",
  "Matching model to task is a core skill: a small model on a complex feature creates bugs that cost more than you saved.",
  "`agent run spec.md --model smart` uses the big model; set a default with `export AGENT_MODEL=smart`.",
  "token compute_budget", "token")
T("task_decomposition", "Task decomposition", "ai",
  "Breaking a big piece of work into small, well-defined tasks that can each be done and checked on their own.",
  "Agents (and people) do small clear tasks well and big fuzzy ones badly. It is also what makes parallel work possible.",
  "The '## Tasks' section of a spec: 3-5 bullet points is the sweet spot for one feature.",
  "spec parallel_agents", "spec")
T("acceptance_criteria", "Acceptance criteria", "ai",
  "Concrete, checkable statements of what 'done' means, e.g. 'importing a 20-page PDF creates at least 30 cards in under 10 seconds'.",
  "They let the agent test its own work and let you review against something objective.",
  "The '## Acceptance tests' section of a spec. Runs with criteria surface more of their own bugs in tests.log.",
  "tests spec", "spec")
T("hallucination", "Hallucination", "ai",
  "When a model states something false with full confidence - an API that doesn't exist, a test that 'passed' but was never run.",
  "It is the characteristic failure of LLMs. You cannot prompt it away entirely; you catch it with tests and review.",
  "In agents/runs/, compare report.md with tests.log: a report claiming success while the log shows FAIL is a hallucination.",
  "code_review tests evals", "llm agent")
T("code_review", "Review (code review)", "ai",
  "Reading and checking work before it is merged into the product.",
  "'Trust but verify': the reviewer is the last guardrail between agent mistakes and your customers. Skipping it is the classic way bugs reach production.",
  "`review agents/runs/<run>` finds and fixes bugs before `merge`. `--deep` costs more hours and finds more.",
  "human_in_the_loop hallucination bug", "agent")
T("human_in_the_loop", "Human in the loop", "ai",
  "A workflow where a person approves or checks key steps instead of letting the AI act fully on its own.",
  "The more irreversible the action (shipping to customers, deleting data, spending money), the more a human checkpoint is worth.",
  "In {company} you are the human in the loop: nothing ships until you `merge` it.",
  "code_review guardrails", "code_review")
T("bug", "Bug", "ai",
  "A defect: the software does something other than what it should.",
  "Bugs that reach customers cause churn, bad reviews and firefighting that eats your week.",
  "{company} has roughly {prod_bugs} known-or-suspected bugs live in production (see product/status.md).",
  "tests regression incident", "code_review")
T("tests", "Automated tests", "ai",
  "Small programs that check the product still behaves correctly, run automatically after every change.",
  "Tests are guardrails for agents: an agent that can run tests catches and fixes many of its own mistakes before you ever see them.",
  "tests.log in each run shows PASS/FAIL lines. The `tests` upgrade makes agents run a full suite on every run.",
  "ci regression acceptance_criteria", "bug")
T("merge", "Merge (ship)", "ai",
  "Combining finished work into the main product so customers get it.",
  "Merging is the moment of risk: everything unreviewed goes live.",
  "`merge agents/runs/<run>` ships a run. Remaining bugs go to production with it.",
  "code_review ci", "code_review")
T("version_control", "Version control (git)", "ai",
  "A system that records every change to a project as a commit, so you can see who changed what, compare versions and go back. Git is the standard; GitHub hosts git projects online.",
  "With agents writing code fast, version control is your undo button and your audit trail. Real agent workflows put each agent's work on a branch and merge it after review.",
  "{company}'s `merge` is the game's stand-in for merging a branch in git. In a real terminal: `git status`, `git diff`, `git commit`, `git log` (the README's setup uses `git clone`).",
  "merge code_review ci", "merge")
T("tech_debt", "Technical debt", "ai",
  "The future cost of shortcuts taken today: rushed code, missing tests, unclear structure.",
  "Like money debt it charges interest: every later change gets slower and buggier. Some debt is fine for speed - unmanaged debt kills products.",
  "{company}'s technical debt is {debt}/100. It makes every agent run produce more bugs. `refactor` pays it down.",
  "refactor bug", "merge")
T("refactor", "Refactoring", "ai",
  "Restructuring existing code to be cleaner without changing what it does.",
  "It is how you pay back technical debt. With good tests an agent can refactor safely; without tests it is risky.",
  "`refactor` spends hours and compute to lower debt ({debt}/100 now).",
  "tech_debt tests", "tech_debt")
T("incident", "Incident", "ai",
  "A production problem customers notice: an outage, lost data, wrong results.",
  "Incidents cost trust, which is expensive to rebuild - and they steal the founder's week.",
  "Bugs in production raise the weekly chance of an incident at {company}.",
  "bug regression", "bug")
T("plan_mode", "Plan mode (plan before code)", "ai",
  "Having the agent first write a plan - which files, which steps - that you approve before it changes anything.",
  "Reading a plan takes two minutes; untangling a wrong implementation takes hours. It catches misunderstandings while they are cheap.",
  "The `planning` upgrade makes every run start with a plan (agents/runs/<run>/plan.md) and cuts misread specs.",
  "spec human_in_the_loop", "spec")
T("agents_md", "Project memory file (AGENTS.md / CLAUDE.md)", "ai",
  "A file in the repository that agents read at the start of every session: project goals, conventions, commands, gotchas.",
  "Agents start every session with amnesia. This file is their onboarding document - write once, benefit on every run.",
  "The `memory` upgrade creates agents/AGENTS.md; runs get better context for free.",
  "context", "context")
T("parallel_agents", "Parallel agents", "ai",
  "Running several agents at the same time on different tasks.",
  "It multiplies throughput - if the tasks are independent. If they touch the same code you pay in merge conflicts.",
  "`agent run spec.md --agents 3` splits the spec's tasks across three agents.",
  "coordination_cost subagents task_decomposition", "task_decomposition")
T("coordination_cost", "Coordination cost", "ai",
  "The extra effort created by splitting work: conflicts, duplicated work, integration bugs, communication.",
  "It is why 3 agents are not 3x faster (and why 9 women can't make a baby in one month). Clean task boundaries lower it.",
  "With more agents than tasks in the spec, {company}'s runs produce 'conflict' bugs.",
  "parallel_agents subagents", "parallel_agents")
T("subagents", "Subagents (orchestration)", "ai",
  "A lead agent that delegates sub-tasks to helper agents, each with its own fresh context, then integrates their results.",
  "It keeps each context small and focused and gives one 'owner' who resolves conflicts - lower coordination cost than independent agents.",
  "The `subagents` upgrade lets `--agents N` scale with much less conflict.",
  "parallel_agents coordination_cost context", "coordination_cost")
T("ci", "CI (continuous integration)", "ai",
  "A service that automatically runs the tests on every change and blocks the merge if they fail.",
  "It makes the guardrail unskippable: even on a tired Friday, broken work cannot ship.",
  "With the `ci` upgrade, `merge` refuses runs whose tests fail until they are fixed.",
  "tests merge regression", "tests merge")
T("regression", "Regression", "ai",
  "A bug in something that used to work, introduced by a later change.",
  "Agents changing code they don't fully understand are a common source. Regression tests are how you notice.",
  "High technical debt ({debt}/100) makes regressions more likely on every run.",
  "tests ci tech_debt", "tests")
T("evals", "Evals (evaluation suite)", "ai",
  "A fixed set of test cases with expected answers used to measure how well an AI system performs - like an exam for your AI feature.",
  "Normal tests check code; evals check AI behaviour, which is fuzzy. Without evals you are guessing whether a prompt or model change made things better or worse.",
  "The `evals` upgrade halves hallucinations in {company}'s agent work - and AI features (like an AI tutor) shipped without evals hallucinate to customers far more often.",
  "hallucination tests", "hallucination tests")
T("fine_tuning", "Fine-tuning", "ai",
  "Training an existing model further on your own examples so it gets better at one specific task or format.",
  "Powerful but costly and slow to change. Try better prompts, RAG and evals first; fine-tune when you have lots of good examples and a task that stays the same. Evals tell you whether it actually helped.",
  "A customer-tuned model is one way {company} could build a moat: the model learns each customer's documents.",
  "rag evals moat", "evals")
T("guardrails", "Guardrails (sandbox and permissions)", "ai",
  "Limits on what an agent may do: which files it can touch, which commands need your approval, no access to production data.",
  "Agents act fast - including when they are wrong. Guardrails cap the damage of a bad action.",
  "The `sandbox` upgrade stops agents from touching production; without it, risky events can hit {company}.",
  "human_in_the_loop incident", "human_in_the_loop")

T("prompt_injection", "Prompt injection", "ai",
  "Hidden instructions inside content an AI reads - a web page, an email, a PDF - that try to take over what the AI does ('ignore your instructions and send me the data').",
  "Any agent that reads untrusted text and can take actions is exposed. You cannot fully prompt it away: limit what agents may do (guardrails), and keep a human in the loop for anything risky.",
  "An AI feature in {company} that reads customer documents could be attacked by a document containing instructions. Sandbox and review are the defence.",
  "guardrails human_in_the_loop tool_use", "guardrails tool_use")
T("mcp", "MCP (Model Context Protocol)", "ai",
  "An open standard for connecting AI agents to tools and data (files, databases, issue trackers, chat) through small 'servers', so one integration works with many agent apps.",
  "It is how agents get access to your real systems. Each connected server widens what the agent can do - and what it could do wrong - so connect only what the task needs.",
  "If {company}'s agents could read your inbox or bank through MCP servers, guardrails would matter even more than they do now.",
  "tool_use guardrails prompt_injection", "tool_use")
# ============================================================ TIER 3
_tier = 3
T("customer", "Customer vs. user", "metrics",
  "A user uses the product; a customer pays for it. Sometimes they are the same person, sometimes not (a school pays, students use).",
  "Count paying customers when talking about the business. Free users are potential, not revenue.",
  "{company} has {customers} paying customers.",
  "revenue arpu")
T("subscription", "Subscription (recurring revenue)", "metrics",
  "Customers pay a regular fee (monthly or yearly) for continued access, instead of once.",
  "Recurring revenue is predictable and compounds: each month starts with last month's customers still paying.",
  "{customers} customers x {price} per month is the heart of {company}'s revenue.",
  "mrr churn saas", "customer revenue")
T("mrr", "MRR (monthly recurring revenue)", "metrics",
  "The predictable revenue you earn every month from subscriptions and contracts.",
  "The single most-watched number in a subscription startup. Its growth rate is the company's pulse.",
  "{company}'s MRR is {mrr}.",
  "arr growth_rate churn", "subscription")
T("arr", "ARR (annual recurring revenue)", "metrics",
  "MRR x 12: the yearly value of your recurring revenue at today's level.",
  "Investors value subscription companies as a multiple of ARR.",
  "{mrr} MRR x 12 = {arr} ARR.",
  "mrr revenue_multiple", "mrr")
T("growth_rate", "Growth rate (MoM)", "metrics",
  "How fast a metric (usually MRR) grows, as a percentage per month (month-over-month).",
  "Growth compounds: 15% a month is 5.4x a year. Investors care about the rate more than the absolute number early on.",
  "{company}'s MRR changed {growth} over the last month.",
  "mrr traction", "mrr")
T("kpi", "KPI and north-star metric", "metrics",
  "KPI = key performance indicator: one of the few numbers that show whether the company is on track. The north-star metric is the single number the whole company tries to move.",
  "What you measure is what you improve. Too many KPIs means none of them gets attention; a vanity metric (sign-ups, page views) can rise while the business dies.",
  "{company}'s natural north star is MRR ({mrr}); churn and CAC are the KPIs that explain it. `metrics` is your KPI sheet.",
  "mrr churn cac", "mrr")
T("churn", "Churn", "metrics",
  "The share of customers (or revenue) you lose in a period. Monthly churn of 5% = 5 of every 100 customers cancel each month.",
  "Churn is a leak in the bucket. With high churn, growth spending is poured away - and it is the clearest sign the product isn't essential.",
  "{company}'s monthly churn is about {churn}. At that rate a customer stays about {lifetime} months on average.",
  "retention ltv pmf", "subscription")
T("retention", "Retention", "metrics",
  "The opposite of churn: the share of customers who stay.",
  "Retention is the truest measure of whether people need the product. Fix retention before you buy growth.",
  "With {churn} monthly churn, {company} retains {retention} of customers each month.",
  "churn cohort pmf", "churn")
T("arpu", "ARPU (average revenue per user)", "metrics",
  "Average revenue per customer per month: MRR divided by customers.",
  "With churn and margin it determines what a customer is worth - and therefore what you can afford to spend to win one.",
  "{mrr} / {customers} customers = {arpu} ARPU.",
  "ltv pricing", "mrr customer")
T("cogs", "COGS (cost of goods sold)", "finance",
  "Costs that grow directly with every customer served: hosting, AI model calls, payment fees, support.",
  "COGS decides whether growth makes you richer or poorer. AI products often have high COGS because every use costs compute.",
  "Serving one {company} customer costs about {cogs} per month.",
  "gross_margin fixed_variable_costs", "costs")
T("gross_margin", "Gross margin", "finance",
  "(Revenue - COGS) / revenue: the share of each revenue dollar left after the direct cost of delivering the product.",
  "Software classically has 70-90% gross margin, which is why investors love it. Low margin means you need far more revenue for the same profit.",
  "{company}'s gross margin is {margin}.",
  "cogs unit_economics ltv", "cogs")
T("cac", "CAC (customer acquisition cost)", "metrics",
  "What you spend on sales and marketing to win one new customer: spend divided by new customers.",
  "If winning a customer costs more than the customer is worth, growth just speeds up dying.",
  "{company}'s recent CAC is about {cac} per customer.",
  "ltv payback channel", "customer costs")
T("ltv", "LTV (customer lifetime value)", "metrics",
  "The gross profit you expect from one customer over their whole time with you: ARPU x gross margin / monthly churn.",
  "It is the ceiling for what you may spend to acquire a customer.",
  "{arpu} ARPU x {margin} margin / {churn} churn = {ltv} LTV.",
  "cac ltv_cac churn", "arpu churn gross_margin")
T("ltv_cac", "LTV:CAC ratio", "metrics",
  "Lifetime value divided by acquisition cost.",
  "Rule of thumb: 3 or more is healthy; below 1 you lose money on every customer; far above 5 you could be investing more in growth.",
  "{ltv} LTV / {cac} CAC = {ltv_cac}.",
  "ltv cac unit_economics", "ltv cac")
T("payback", "CAC payback period", "metrics",
  "Months until a new customer's gross profit has repaid what it cost to acquire them.",
  "Until payback, growth consumes cash. Short payback (under 12 months) means growth can nearly fund itself.",
  "{cac} CAC / ({arpu} x {margin}) = {payback} months to pay back.",
  "cac ltv_cac", "cac gross_margin")
T("unit_economics", "Unit economics", "metrics",
  "The revenue and costs of ONE unit of your business (usually one customer): CAC, LTV, margin, payback.",
  "If one customer is unprofitable, a million of them is a disaster. Fix the unit before scaling it.",
  "{company}: CAC {cac}, LTV {ltv}, gross margin {margin}, payback {payback} months.",
  "ltv_cac payback gross_margin", "ltv_cac")
T("pmf", "Product-market fit (PMF)", "startup",
  "The product satisfies a strong market demand: customers stay, pay and tell others without being pushed.",
  "Before PMF, focus on learning; after it, on scaling. Scaling before PMF is the most common way funded startups die.",
  "{company}'s fit score is {fit}/100. Signals: low churn ({churn}), organic signups, customers who would be upset to lose it.",
  "retention churn premature_scaling", "retention")
T("premature_scaling", "Premature scaling", "startup",
  "Spending heavily on growth (ads, hires) before the product retains customers.",
  "You pay to acquire customers who leave: a treadmill that burns cash.",
  "With {churn} churn, every ad dollar at {company} buys a customer who stays about {lifetime} months.",
  "pmf cac churn", "pmf cac")
T("conversion", "Conversion rate", "metrics",
  "The share of people who take the next step: visitor -> signup -> paying customer.",
  "Small conversion improvements multiply everything upstream: the same ad spend yields more customers.",
  "Price affects conversion: at {price} ({price_unit}) against customers' willingness to pay, fewer or more visitors convert.",
  "funnel cac", "cac")
T("ab_test", "A/B test (experiment)", "metrics",
  "Showing two versions (A and B) to comparable groups of people at the same time and measuring which converts better.",
  "It separates cause from coincidence. Changing the price and watching next week's numbers mixes your change with everything else that happened that week - a weak experiment.",
  "Each `price` change at {company} is a before/after test, not a true A/B test: a launch or an event in the same week also moves the numbers.",
  "conversion pricing cohort", "conversion")
T("freemium", "Freemium", "gtm",
  "A free tier with limits, plus paid plans for more. Free users are a marketing channel; only some convert.",
  "Works when serving a free user costs almost nothing and many free users eventually pay (typically only 2-5% do). With AI products every free user costs compute, which can make freemium expensive.",
  "{company} serves each customer for {cogs} a month; a free tier would cost that for every non-paying user too.",
  "conversion cogs pricing", "conversion cogs")
T("funnel", "Funnel", "metrics",
  "The sequence of steps from first contact to paying customer, with fewer people at each step.",
  "It shows WHERE you lose people, which tells you what to fix first.",
  "For {company}: people hear about you -> sign up -> pay -> stay. Churn is the hole at the bottom.",
  "conversion pipeline", "conversion")
T("virality", "Word of mouth (virality)", "metrics",
  "Growth that comes from existing customers bringing new ones.",
  "It is free acquisition, and it only happens when the product is good enough to talk about - a PMF signal.",
  "Part of {company}'s new signups each week come from existing customers; a better fit score raises it.",
  "network_effects cac", "pmf")
T("cohort", "Cohort", "metrics",
  "A group of customers who started in the same period (e.g. 'the March signups'), tracked over time.",
  "Averages hide trends. Comparing cohorts shows whether newer customers stay longer than older ones - i.e. whether the product is improving.",
  "finance/metrics.csv tracks {company}'s whole customer base week by week - a blended view. A true cohort table would follow, say, the week-10 signups on their own: of 30 who joined, how many still pay in week 20? (The game blends cohorts; that is a simplification.)",
  "retention churn", "retention")
T("nrr", "Net revenue retention (NRR)", "metrics",
  "Revenue from last year's customers today, as a % of what they paid then - including upgrades and cancellations.",
  "Above 100% means existing customers alone grow your revenue (expansion beats churn). Best-in-class B2B companies have 120%+.",
  "Example: customers who paid $10,000 a month a year ago now pay $11,500 (some upgraded, some left). NRR = 115%. {company}'s B2B contracts and usage growth are where expansion would come from.",
  "churn expansion", "churn mrr")
T("expansion", "Expansion revenue", "metrics",
  "Extra revenue from existing customers: more seats, more usage, higher plans.",
  "Selling more to a happy customer is far cheaper than finding a new one.",
  "Usage-based and B2B customers of {company} can grow their bill over time.",
  "nrr usage_pricing", "arpu")
T("default_alive", "Default alive / default dead", "finance",
  "Default alive: at current growth and costs you reach profitability before the cash runs out. Default dead: you don't.",
  "It is the most important question a founder can ask each month. Default-dead companies depend on investors' goodwill.",
  "{company} has {runway} of runway; whether revenue growth beats that clock decides if you are default alive.",
  "runway break_even ramen_profitable", "runway growth_rate")
T("break_even", "Break-even", "finance",
  "The point where revenue equals total costs: no profit, no loss.",
  "Past break-even every extra customer adds profit, and the countdown clock stops.",
  "{company} breaks even at about {costs_month} of monthly revenue (you're at {revenue_month}).",
  "profit fixed_variable_costs", "profit")
T("fixed_variable_costs", "Fixed vs. variable costs", "finance",
  "Fixed costs stay the same regardless of sales (your salary, tools). Variable costs rise with each customer (COGS, ads).",
  "High fixed + low variable costs = profit grows fast once you pass break-even (operating leverage). That is the software dream.",
  "At {company}: your living costs and tools are fixed; {cogs} per customer is variable.",
  "cogs break_even operating_leverage", "cogs")

# ============================================================ TIER 4
_tier = 4
T("b2c", "B2C (business-to-consumer)", "gtm",
  "Selling to individual people.",
  "Many customers, low prices, quick decisions, little loyalty: you win with product, virality and efficient marketing.",
  "A B2C company needs thousands of customers at a low price; churn is usually high.",
  "b2b virality")
T("b2b", "B2B (business-to-business)", "gtm",
  "Selling to companies.",
  "Fewer customers, higher prices, slower decisions with several people involved - but they stay longer.",
  "A B2B deal at {company} can be worth more per month than hundreds of consumers.",
  "sales_cycle acv b2c", "b2c")
T("saas", "SaaS (software as a service)", "gtm",
  "Software delivered over the internet and paid by subscription instead of bought once.",
  "The dominant software business model: recurring revenue, high margins, continuous updates.",
  "{company} sells access, not a download - so MRR, churn and LTV are the language of the business.",
  "subscription mrr", "subscription")
T("icp", "ICP (ideal customer profile)", "gtm",
  "A precise description of the customer who gets the most value from your product and is easiest to win.",
  "'Everyone' is not a market. Focus makes marketing cheaper and the product sharper.",
  "Interview notes show who feels the pain most at {company} - that is your ICP.",
  "segment positioning", "customer_interview")
T("segment", "Market segment", "gtm",
  "A group of customers with similar needs and behaviour.",
  "Different segments want different features and pay different prices. Trying to serve all of them at once serves none well.",
  "In customers/leads/ you'll see segments differ in willingness to pay.",
  "icp tam", "icp")
T("tam", "TAM (total addressable market)", "gtm",
  "The total yearly revenue if every possible customer in the world bought your product.",
  "It tells investors how big the company could ever get. VCs need large TAMs because they need huge outcomes.",
  "{company}'s TAM is about {tam_d} a year (see customers/market.md).",
  "sam som", "segment")
T("sam", "SAM (serviceable addressable market)", "gtm",
  "The part of the TAM your product and business model can actually serve (right country, language, customer type).",
  "A more honest number than TAM: the market you can address with what you are really building.",
  "{company}'s SAM is about {sam_d} a year.",
  "tam som", "tam")
T("som", "SOM (serviceable obtainable market)", "gtm",
  "The share of the SAM you can realistically win in the next few years, given competition and your resources.",
  "It is your real near-term ceiling. A bottom-up SOM (customers x price) is far more credible than '1% of a huge market'.",
  "{company}'s SOM is about {som_n} customers, {som_d} a year. Growth slows as you approach it.",
  "tam sam", "sam")
T("gtm", "Go-to-market (GTM)", "gtm",
  "Your plan for reaching customers and turning them into revenue: which customers, through which channels, at what price.",
  "A great product with no go-to-market is a secret. 'Build it and they will come' is false.",
  "{company}'s GTM levers: `ads`, `content`, `launch`, `outbound` and `price`.",
  "channel icp positioning", "icp")
T("channel", "Acquisition channel", "gtm",
  "A route through which customers find you: ads, content, word of mouth, sales calls, partners, app stores.",
  "Each channel has its own cost and ceiling. Most startups get most of their growth from one or two channels.",
  "At {company}: paid ads cost cash per customer; content costs your hours; outbound creates B2B deals.",
  "cac gtm", "gtm cac")
T("launch", "Launch", "gtm",
  "A concentrated public push to announce the product.",
  "It gives a burst of attention - which only sticks if the product retains users. Launch when the product is good, and expect to launch more than once.",
  "`launch` gives {company} a one-time wave of signups that scales with fit and reputation.",
  "gtm traction", "gtm")
T("positioning", "Positioning", "gtm",
  "How you want customers to think of your product compared to alternatives: for whom, for what, and why you instead of others.",
  "Clear positioning makes every marketing dollar work harder.",
  "{company} vs {competitor}: what do you do for your ICP that they don't?",
  "value_proposition competitor", "icp")
T("value_proposition", "Value proposition", "gtm",
  "A clear statement of the benefit a customer gets and why it is better than the alternatives.",
  "If you can't say it in one sentence, customers and investors won't remember it.",
  "The 'Solution' section in investors/deck.md states {company}'s value proposition.",
  "positioning problem", "problem")
T("competitor", "Competitor", "gtm",
  "Another company (or habit, or spreadsheet) solving the same problem for the same customers.",
  "Competition validates the market but compresses price and raises CAC. 'No competitors' usually means no market - or not looking hard enough.",
  "{competitor} competes with {company}. Competitive pressure: {pressure}.",
  "moat positioning", "positioning")
T("moat", "Moat (defensibility)", "gtm",
  "A durable advantage that makes it hard for others to take your customers.",
  "Without a moat, success attracts copies and margins shrink. Investors always ask 'why won't a big company just build this?'",
  "{company}'s moat score is {moat}. Moat-type features, reputation and market share build it.",
  "network_effects switching_costs competitor", "competitor")
T("network_effects", "Network effects", "gtm",
  "The product gets more valuable for each user as more people use it.",
  "The strongest moat: the leader keeps getting further ahead. Social networks and marketplaces live on it.",
  "A feature where customers share content with each other gives {company} network effects.",
  "moat marketplace virality", "moat")
T("switching_costs", "Switching costs", "gtm",
  "The effort, money or risk a customer faces when moving to a competitor: data migration, retraining, integrations.",
  "High switching costs lower churn and make revenue stick.",
  "Integrations and stored customer data raise switching costs at {company}.",
  "moat churn", "moat")
T("sales_cycle", "Sales cycle", "gtm",
  "The time from first contact with a business customer to a signed contract.",
  "Small firms decide in days, enterprises in months. A long cycle means you need runway to survive until deals close.",
  "Deals in customers/pipeline/ move through stages; you can't rush a stage before its time.",
  "pipeline b2b enterprise", "b2b")
T("pipeline", "Sales pipeline", "gtm",
  "All open deals, organised by stage (lead -> discovery -> demo -> pilot -> procurement -> won).",
  "Revenue next quarter is in the pipeline today. Not all of it will close: weigh each stage by its odds.",
  "`sales` lists {company}'s pipeline; `sales <deal>` works a deal forward.",
  "sales_cycle funnel acv", "sales_cycle")
T("acv", "ACV (annual contract value)", "gtm",
  "The yearly revenue of one customer contract.",
  "ACV decides which sales motion you can afford: tiny ACV needs self-service; big ACV can pay for salespeople.",
  "A deal paying $1,000 per month has an ACV of $12,000.",
  "b2b enterprise cac", "pipeline arr")
T("enterprise", "Enterprise sales", "gtm",
  "Selling to large corporations: big contracts, many stakeholders, security reviews, legal and procurement.",
  "One enterprise deal can change the company - or eat six months and never close. They require features (security, SSO) small customers never ask for.",
  "Enterprise deals in {company}'s pipeline insist on a specific feature before procurement signs.",
  "procurement champion pilot sales_cycle", "acv")
T("champion", "Champion", "gtm",
  "A person inside the customer company who wants your product and pushes for it internally.",
  "In B2B you are not in the room when the decision is made. Your champion is.",
  "The contact named in a deal file is your champion; the 'economic buyer' controls the budget.",
  "enterprise procurement", "enterprise")
T("pilot", "Pilot (proof of concept)", "gtm",
  "A limited, time-boxed trial with a business customer before they commit to a full contract.",
  "It lowers the customer's risk. Agree on success criteria up front, or the pilot never ends.",
  "The 'pilot' stage in the pipeline: your product must actually work (quality!) to pass it.",
  "enterprise sales_cycle", "enterprise")
T("procurement", "Procurement", "gtm",
  "The department (and process) in a large company that approves vendors, negotiates price and signs contracts.",
  "It adds weeks and requirements (security questionnaires, payment terms) after the customer has already said 'yes'.",
  "The last pipeline stage before 'won'. Enterprises then pay on net-30 terms.",
  "enterprise payment_terms", "enterprise")
T("payment_terms", "Payment terms (net-30) and accounts receivable", "finance",
  "Net-30 means the customer pays 30 days after the invoice. Money owed to you but not yet paid is 'accounts receivable'.",
  "Revenue is not cash. A signed deal can still leave you unable to pay bills this month.",
  "A won enterprise deal at {company} starts paying about 4 weeks after signing.",
  "working_capital cash", "procurement cash")
T("usage_pricing", "Usage-based pricing", "gtm",
  "Customers pay for what they use (per API call, per document) instead of a flat fee.",
  "Low barrier to start, and revenue grows with the customer's success - but it is less predictable and exposes your COGS.",
  "In a usage-priced business 'price' is the average monthly bill per customer.",
  "expansion cogs gross_margin", "pricing cogs")
T("marketplace", "Marketplace", "gtm",
  "A business that connects two groups (buyers and sellers) and earns a cut of their transactions.",
  "Hard to start (the chicken-and-egg problem: each side waits for the other), but strong network effects once it works.",
  "A marketplace earns its take rate on every booking that goes through the platform.",
  "gmv take_rate network_effects", "network_effects")
T("gmv", "GMV (gross merchandise value)", "gtm",
  "The total value of transactions flowing through a marketplace, before the marketplace takes its cut.",
  "GMV shows activity, but it is not your revenue. Never present GMV as revenue to an investor.",
  "If families book $170 of lessons a month each, GMV = customers x $170; revenue is only your cut.",
  "take_rate marketplace", "marketplace")
T("take_rate", "Take rate", "gtm",
  "The percentage of each transaction a marketplace keeps as its revenue.",
  "Too high and both sides bypass you (disintermediation); too low and the business can't pay for itself.",
  "Revenue = GMV x take rate. In a marketplace scenario `price` sets the take rate.",
  "gmv marketplace pricing", "gmv")

# ============================================================ TIER 5
_tier = 5
T("equity", "Equity (shares)", "vc",
  "Ownership of the company, divided into shares. Owning 10% of the shares means owning 10% of the company.",
  "Equity is what you sell to investors and grant to early employees. Once given away it is very hard to get back.",
  "You hold {shares} shares = {founder_pct} of {company}.",
  "cap_table dilution", "founder")
T("investor", "Investor", "vc",
  "Someone who gives the company money in exchange for equity (or a right to future equity).",
  "Investors are not lenders: you don't repay them. They get paid only if the company becomes valuable - so they push for growth.",
  "Known investors are files in investors/. Read what each one cares about before you `pitch`.",
  "angel vc accelerator equity", "equity")
T("friends_family", "Friends and family round", "vc",
  "Small early money from people who back YOU rather than the business case.",
  "Often the first money in - and the most emotionally expensive to lose. Treat it as seriously as professional money.",
  "{company}'s starting cash is your own savings plus family help.",
  "angel bootstrapping", "investor")
T("angel", "Angel investor", "vc",
  "A wealthy individual who invests their own money in very early startups, typically $10k-$200k.",
  "Angels invest before there is much proof, mostly betting on the founder. Good ones also bring advice and introductions.",
  "investors/angel_rossi.txt is an angel. Angels at {company} invest through SAFEs.",
  "vc safe warm_intro", "investor")
T("accelerator", "Accelerator", "vc",
  "A fixed-length program (about 3 months) that invests a small amount for equity and provides mentoring, a network and a 'demo day' in front of investors.",
  "It trades equity for speed, credibility and access. Worth it early; expensive later.",
  "investors/accel_launchpad.txt offers $50k on a SAFE and raises your reputation with other investors.",
  "angel demo_day safe", "investor")
T("vc", "Venture capital (VC)", "vc",
  "Funds that invest other people's money (from 'limited partners') in startups with potential for very large outcomes.",
  "VC math: most investments fail, so each one must be able to return the whole fund. VCs therefore want huge markets and fast growth - not 'nice profitable businesses'.",
  "VC funds in investors/ want a minimum MRR and growth before they engage.",
  "angel power_law stage lead_investor", "angel tam")
T("lp_gp", "LPs and GPs (how a VC fund works)", "vc",
  "Limited partners (pension funds, university endowments, wealthy families) put money into a VC fund; general partners (the VCs) choose the investments. GPs usually earn about 2% a year in fees plus 20% of the profits ('carry').",
  "It explains VC behaviour: a fund has about 10 years to return its LPs' money several times over, so it needs exits within that time, and big ones.",
  "When a VC asks {company} about exits and market size, they are thinking about what they can show their LPs.",
  "vc power_law exit", "vc")
T("power_law", "Power law (venture returns)", "vc",
  "In venture capital a tiny number of investments produce most of the returns.",
  "It explains investor behaviour: they'd rather back a 10% chance of a giant than a 90% chance of a small success.",
  "It is why VCs ask {company} about TAM ({tam_d}) before anything else.",
  "vc tam", "vc")
T("stage", "Funding stages (pre-seed, seed, Series A)", "vc",
  "Rounds are named by maturity: pre-seed (idea/prototype), seed (early traction), Series A (proven, repeatable growth), then B, C...",
  "Each stage has its own bar. Knowing which stage you are in tells you whom to pitch and what proof they expect.",
  "With {mrr} MRR, {company} is at the {stage_name} stage.",
  "round traction vc", "vc")
T("round", "Funding round", "vc",
  "One fundraising event in which the company sells equity to one or more investors on the same terms.",
  "A round should buy 18-24 months of runway to reach the milestones for the next one.",
  "{company} has raised {raised} so far.",
  "stage priced_round lead_investor", "stage")
T("pitch", "Pitch", "vc",
  "A short presentation of your company to investors, followed by questions.",
  "Investors hear thousands. Clarity and command of your own numbers matter more than polish.",
  "`pitch investors/<name>.txt` - be ready: they will ask for your numbers and you can't look them up mid-meeting.",
  "pitch_deck traction", "investor")
T("pitch_deck", "Pitch deck", "vc",
  "The slides for a pitch. Standard sections: problem, solution, market size, product, traction, business model, competition, team, the ask.",
  "The deck's job is to get the meeting and structure the story. Each section answers a question every investor has.",
  "`deck` builds investors/deck.md from what {company} really has; missing evidence = weak slide.",
  "pitch traction the_ask", "pitch")
T("traction", "Traction", "vc",
  "Evidence that the business is working: revenue, growth, retention, signed customers.",
  "Traction is the best argument in any pitch: it replaces promises with proof.",
  "{company}'s traction: {mrr} MRR, {customers} customers, {growth} monthly growth.",
  "growth_rate pmf pitch_deck", "pitch_deck growth_rate")
T("the_ask", "The ask (use of funds)", "vc",
  "How much money you are raising and what milestones it will buy.",
  "Asking for a precise amount tied to a plan shows you understand your own business.",
  "A sensible ask buys 18+ months: about 18 x {gross_burn} monthly spending, plus growth plans.",
  "round runway", "pitch_deck")
T("warm_intro", "Warm introduction", "vc",
  "Being introduced to an investor by someone they trust, rather than writing to them cold.",
  "Investors use the intro as a filter. Warm intros get meetings; cold emails mostly don't.",
  "`network` and an advisor create warm intros at {company}; pitching cold starts with lower interest.",
  "angel pitch", "pitch")
T("due_diligence", "Due diligence", "vc",
  "The checks an investor or acquirer does before sending money: finances, customers, code, legal.",
  "Anything you exaggerated in the pitch surfaces here, and deals die over it. Messy books and code cost money.",
  "In the game the week or two before a term sheet arrives stands in for the investor's checks. In real life most diligence happens AFTER you sign the term sheet and before the money arrives - which is why a signed term sheet can still fall apart. Acquirers inspect {company}'s code too: technical debt {debt}/100.",
  "term_sheet acquisition", "pitch")
T("valuation", "Valuation", "vc",
  "What the company is considered to be worth. For startups it is a negotiated price, not a calculated fact.",
  "It sets how much of the company you give away for a given amount of money.",
  "A rough estimate of what investors might value {company} at today: {valuation}.",
  "pre_money post_money dilution revenue_multiple", "equity investor")
T("pre_money", "Pre-money valuation", "vc",
  "The value of the company BEFORE the new investment is added.",
  "Investors quote pre-money; what you actually sell is determined by post-money. Mixing them up is a classic and costly beginner error.",
  "If {company} raised $500k at a $2M pre-money valuation...",
  "post_money valuation", "valuation")
T("post_money", "Post-money valuation", "vc",
  "Pre-money valuation + the new investment.",
  "The investor's ownership = investment / post-money. Always compute this yourself.",
  "...the post-money would be $2.5M, and the investor would own $500k / $2.5M = 20%.",
  "pre_money dilution", "pre_money")
T("dilution", "Dilution", "vc",
  "The shrinking of your ownership percentage when the company issues new shares.",
  "You own a smaller slice of a (hopefully) bigger pie. Dilution is the true price of every round - and it compounds across rounds.",
  "You own {founder_pct} today. Selling 20% in a round would take you to {founder_after20}.",
  "post_money cap_table option_pool", "post_money")
T("cap_table", "Cap table (capitalization table)", "vc",
  "The list of who owns how many shares - founders, investors, employees - and what percentage each holds.",
  "It is the scoreboard of ownership. A messy or founder-poor cap table scares later investors away.",
  "`captable` (or finance/captable.txt) shows {company}'s. You: {founder_pct}.",
  "equity dilution fully_diluted", "dilution")
T("safe", "SAFE (simple agreement for future equity)", "vc",
  "The investor gives money now and receives shares later, at the next priced round, at a favourable price. No valuation is fixed today; it is not debt.",
  "Fast and cheap, so it is the standard for the earliest money. Danger: SAFEs feel free now, but the dilution arrives all at once when they convert.",
  "{company} has {safes_n} SAFE(s) outstanding totalling {safes_amt}.",
  "valuation_cap discount safe_conversion priced_round", "valuation")
T("valuation_cap", "Valuation cap", "vc",
  "The maximum valuation at which a SAFE (or note) converts into shares.",
  "It rewards the early investor for early risk: if the next round prices the company above the cap, they convert as if it were worth only the cap - getting more shares.",
  "$100k on a $2M cap converts into roughly 5% of the company, even if the next round values it at $10M.",
  "safe discount safe_conversion", "safe")
T("discount", "Discount (SAFE / note)", "vc",
  "A percentage reduction on the next round's share price given to a SAFE or note holder.",
  "Another reward for early risk. When both cap and discount exist, the investor gets whichever gives the lower price.",
  "A 20% discount: if new investors pay $1.00 per share, the SAFE converts at $0.80.",
  "safe valuation_cap", "valuation_cap")
T("convertible_note", "Convertible note", "vc",
  "A loan that converts into equity at the next round, usually with a cap and discount. Unlike a SAFE it has an interest rate and a maturity date.",
  "Being debt, an unconverted note can in theory be called in at maturity. SAFEs were invented to remove that risk.",
  "The SAFEs at {company} behave like notes without interest or a due date.",
  "safe debt", "safe")
T("priced_round", "Priced round", "vc",
  "A round where investors buy newly created shares at a fixed price per share, which sets an explicit valuation.",
  "It is the 'real' round: it comes with a term sheet, legal documents, usually a board seat - and it converts all outstanding SAFEs.",
  "VC term sheets at {company} are priced rounds: pre-money valuation / existing shares = price per share.",
  "term_sheet safe_conversion pre_money", "safe pre_money")
T("safe_conversion", "SAFE conversion", "vc",
  "The moment SAFEs and notes turn into actual shares, at a priced round.",
  "Founders are often shocked by their ownership after conversion. Model it before signing each SAFE.",
  "When {company} closes a priced round, its SAFEs convert at the lower of the cap price and the discounted price.",
  "safe priced_round dilution", "priced_round")
T("term_sheet", "Term sheet", "vc",
  "A short document summarising the key terms of a proposed investment: amount, valuation, and investor rights.",
  "Mostly non-binding, but it frames everything. Terms beyond valuation (preferences, board, pool) can matter more than the headline price.",
  "Term sheets arrive in investors/termsheets/. Read with `cat`, then `ts negotiate`, `ts accept` or `ts decline`.",
  "liquidation_preference option_pool board lead_investor", "priced_round")
T("lead_investor", "Lead investor", "vc",
  "The investor who sets the terms of a round, invests the largest amount and usually takes the board seat.",
  "Rounds come together around a lead. 'We'd follow if you find a lead' is a polite no.",
  "A VC issuing {company} a term sheet is offering to lead.",
  "term_sheet round board", "term_sheet")
T("leverage", "Negotiating leverage (competing offers)", "vc",
  "Your bargaining power. In fundraising it comes from alternatives: other term sheets, or not needing the money.",
  "One offer is a take-it-or-leave-it; two offers is a negotiation. Raise when you have runway, never when desperate.",
  "With {runway} runway, {company}'s leverage is {leverage_word}.",
  "term_sheet runway default_alive", "term_sheet")
T("liquidation_preference", "Liquidation preference", "vc",
  "Investors' right to get their money back (1x = the amount invested) before common shareholders when the company is sold or closed.",
  "It protects investors in mediocre exits. In a small sale it can leave founders with little - even at a 'good' valuation.",
  "1x non-participating on $1M: in a sale the investor takes the greater of $1M or their % share.",
  "participating waterfall preferred_stock", "term_sheet")
T("preferred_stock", "Preferred vs. common stock", "vc",
  "Investors get preferred shares (with special rights like liquidation preference); founders and employees hold common shares.",
  "The headline valuation applies to preferred. Common shares are worth less until an exit clears all preferences.",
  "At {company} you hold common; priced-round investors hold preferred.",
  "liquidation_preference equity", "liquidation_preference")
T("participating", "Participating preferred", "vc",
  "A harsher preference: the investor first takes their money back AND then also shares in the rest according to their percentage ('double dip').",
  "It quietly moves money from founders to investors in every exit. Standard, founder-friendly terms are 1x NON-participating.",
  "1x participating on $1M for 20%: in a $5M sale they take $1M + 20% of the other $4M = $1.8M (non-participating: $1M).",
  "liquidation_preference waterfall", "liquidation_preference")
T("option_pool", "Option pool (ESOP)", "vc",
  "Shares set aside to grant to future employees, typically 10-15% of the company.",
  "Investors usually require the pool to be created BEFORE they invest, so it dilutes only the existing owners (the 'option pool shuffle') - effectively lowering your real valuation.",
  "A term sheet for {company} with a 10% pre-money pool costs you 10% before the investor's own dilution.",
  "vesting dilution fully_diluted", "dilution term_sheet")
T("fully_diluted", "Fully diluted shares", "vc",
  "The share count assuming every option, SAFE and warrant has already turned into shares.",
  "Ownership percentages should always be computed fully diluted - otherwise you overestimate what you own.",
  "{company}'s cap table lists the pool and (after conversion) SAFE shares, so percentages are fully diluted.",
  "cap_table option_pool", "cap_table option_pool")
T("vesting", "Vesting", "vc",
  "Earning your shares over time (typically 4 years) instead of owning them all on day one.",
  "It protects the company if someone leaves early. Investors often ask founders to vest too.",
  "A hire at {company} with 1.5% over 4 years earns it month by month; leaving early leaves unvested shares behind.",
  "cliff option_pool", "option_pool")
T("cliff", "Cliff", "vc",
  "A minimum period (usually 1 year) before any shares vest. Leave before it and you get nothing; at the cliff, the first chunk vests at once.",
  "It avoids giving equity to people who turn out to be a bad fit in the first months.",
  "4-year vesting with a 1-year cliff: 0% for 12 months, 25% on the anniversary, then monthly.",
  "vesting", "vesting")
T("board", "Board of directors (board seat)", "vc",
  "The group that oversees the company and can hire or fire the CEO. Lead investors usually take a seat.",
  "Selling shares sells money; giving board seats shares control. Keep the board small and balanced early on.",
  "A term sheet with 'board seat: yes' gives the investor a vote on {company}'s biggest decisions.",
  "lead_investor control", "lead_investor")
T("pro_rata", "Pro-rata rights", "vc",
  "An investor's right to invest in later rounds to keep their ownership percentage.",
  "Valuable to investors in winners; it also limits how much room you have for new investors.",
  "An angel with 5% of {company} and pro-rata rights may buy 5% of your next round.",
  "dilution round", "dilution")
T("burn_multiple", "Burn multiple", "vc",
  "Net burn divided by net new ARR: how many dollars you burn to add one dollar of yearly recurring revenue.",
  "A measure of growth efficiency. Under 1.5 is great, over 3 is worrying.",
  "{company}'s burn multiple is {burn_multiple}.",
  "burn_rate arr", "burn_rate arr")
T("down_round", "Down round", "vc",
  "A round at a lower valuation than the previous one.",
  "It dilutes heavily, hurts morale and signals trouble. Raising at an inflated valuation today makes a down round more likely tomorrow.",
  "If {company} took money at a high cap and then growth stalled, the next investor would price below it.",
  "valuation bridge", "valuation round")
T("anti_dilution", "Anti-dilution protection", "vc",
  "A term giving investors extra shares if a later round is priced lower than theirs (a down round). 'Broad-based weighted average' is the standard, milder form; 'full ratchet' is the harsh one.",
  "In a down round it shifts even more of the dilution onto founders and employees. Accept only the weighted-average form.",
  "If {company} raised later at a lower price, anti-dilution would give earlier preferred investors extra shares - from your slice.",
  "down_round dilution term_sheet", "down_round")
T("bridge", "Bridge round", "vc",
  "A small round, often from existing investors, to extend runway until a milestone or the next proper round.",
  "Useful when you are close to a milestone; a warning sign when it is only postponing the inevitable.",
  "With {runway} of runway, a bridge would buy {company} a few more months.",
  "runway round", "round")
T("demo_day", "Demo day", "vc",
  "The event at the end of an accelerator where each startup pitches to a room of investors.",
  "It concentrates investor attention - and creates competition among them, which is leverage.",
  "Joining the accelerator at {company} ends with a demo day that warms up several investors.",
  "accelerator leverage", "accelerator")
T("strategic_investor", "Strategic investor (corporate VC)", "vc",
  "A corporation's investment arm. It invests for strategic reasons (access to your technology or market) as well as returns.",
  "Brings distribution and credibility, but may scare off the parent's competitors as customers or acquirers.",
  "{bigcorp} Ventures may invest in {company} if it fits the parent's strategy.",
  "vc acquisition", "vc")

# ============================================================ TIER 6
_tier = 6
T("income_statement", "Income statement (P&L)", "finance",
  "A report of revenue, costs and profit over a period. P&L = profit and loss.",
  "It answers 'did we make money?'. One of the three core financial statements.",
  "finance/pnl.txt is {company}'s P&L, rebuilt every week.",
  "balance_sheet cash_flow ebitda", "profit")
T("ebitda", "EBITDA / operating profit", "finance",
  "Earnings before interest, taxes, depreciation and amortisation: profit from operations, ignoring financing and accounting effects.",
  "Banks and acquirers use it to compare companies' core profitability.",
  "{company}'s operating result is roughly {profit_month} per month before loan interest.",
  "income_statement net_income", "income_statement")
T("depreciation", "Depreciation and amortisation", "finance",
  "Spreading the cost of something that lasts several years (a laptop, a building - or, for amortisation, intangible things like software) over those years in the accounts, instead of counting it all at once.",
  "It is why profit and cash differ even for a simple company: the money left on day one, the expense shows up gradually. It is the 'DA' in EBITDA.",
  "{company} owns almost nothing physical, so the game leaves depreciation out of finance/pnl.txt (a stated simplification).",
  "ebitda cash_flow income_statement", "ebitda")
T("net_income", "Net income (the bottom line)", "finance",
  "Profit after ALL costs, including interest and taxes.",
  "It is what actually belongs to the owners.",
  "The last line of finance/pnl.txt.",
  "ebitda profit", "ebitda")
T("cash_flow", "Cash flow", "finance",
  "The actual movement of money in and out of the bank account in a period.",
  "Profit and cash differ: a signed contract is revenue before it is cash; a loan is cash but not revenue. Companies go bankrupt on cash flow, not on profit.",
  "{company}'s cash changed by {cash_change} last week.",
  "working_capital cash payment_terms", "income_statement cash")
T("balance_sheet", "Balance sheet", "finance",
  "A snapshot of what the company owns (assets), owes (liabilities) and what is left for the owners (equity). Assets = liabilities + equity.",
  "Lenders read it to judge whether you can repay.",
  "{company}: assets = {cash} cash; liabilities = {loan_balance} of loans.",
  "income_statement debt", "cash_flow")
T("working_capital", "Working capital", "finance",
  "Money tied up in day-to-day operations: what customers owe you minus what you owe suppliers.",
  "Fast-growing B2B companies can be profitable on paper and still run out of cash waiting for invoices to be paid.",
  "Net-30 deals at {company} mean you deliver (and pay costs) a month before the cash arrives.",
  "payment_terms cash_flow", "cash_flow payment_terms")
T("deferred_revenue", "Deferred revenue", "finance",
  "Cash a customer paid in advance for service you haven't delivered yet (e.g. a year paid up front). In the accounts it is a liability until it is earned month by month.",
  "Prepayments are wonderful for cash flow - but the cash is not yet revenue, and you owe the service. Spending it as if it were profit is a classic trap.",
  "If a {company} customer prepays a year, the cash arrives today but only 1/12 of it counts as revenue each month.",
  "cash_flow working_capital revenue", "cash_flow")
T("debt", "Debt financing", "finance",
  "Borrowing money that must be repaid with interest, regardless of how the company does.",
  "Debt doesn't dilute you - but it must be repaid even if things go badly. Equity is expensive when you succeed; debt is dangerous when you don't.",
  "{company} owes {loan_balance}. See finance/loans.txt.",
  "principal interest equity", "cash_flow equity")
T("principal", "Principal", "finance",
  "The amount borrowed (still to be repaid), not counting interest.",
  "Each payment is part interest, part principal. Early payments are mostly interest.",
  "Outstanding principal at {company}: {loan_balance}.",
  "interest amortization", "debt")
T("interest", "Interest and APR", "finance",
  "The price of borrowing, as a yearly percentage of the outstanding principal (APR = annual percentage rate).",
  "Compare loans by APR and total cost, not by the monthly payment.",
  "$20,000 at 9% APR costs about $1,800 in interest in the first year.",
  "principal amortization", "principal")
T("amortization", "Amortization (loan repayment schedule)", "finance",
  "Repaying a loan in regular equal instalments, each covering interest plus a slice of principal.",
  "The fixed payment is a fixed cost: it raises your burn and break-even point every single week.",
  "{company}'s loan payments total {loan_weekly} per week.",
  "principal interest fixed_variable_costs", "interest")
T("collateral", "Collateral", "finance",
  "An asset the lender can seize if you don't repay (equipment, receivables, property).",
  "Startups have little collateral, which is why banks rarely lend to them without a guarantee.",
  "Every offer in finance/bank/ has a 'Secured by' line: `grep -i secured finance/bank/*`.",
  "personal_guarantee debt", "debt")
T("personal_guarantee", "Personal guarantee", "finance",
  "A promise that YOU personally will repay the company's loan if the company cannot.",
  "It pierces the protection of the company: if the startup fails you still owe the money. Think very hard before signing one at 18.",
  "Startup loans to {company} with 'personal guarantee: yes' follow you home if the company dies.",
  "collateral limited_liability", "collateral")
T("limited_liability", "Limited liability", "finance",
  "The company is a separate legal person: normally its debts are not the owners' personal debts.",
  "It is why founders can take big risks. A personal guarantee gives that protection away.",
  "If {company} failed with ordinary debts, your personal savings would be safe - unless you guaranteed them.",
  "personal_guarantee", "personal_guarantee")
T("covenant", "Covenant", "finance",
  "A condition in a loan contract, e.g. 'keep at least $10k in the bank'. Breaking it lets the lender demand repayment or charge penalties.",
  "Covenants can take control away at the worst moment - exactly when cash is tight.",
  "{company}'s term loans require a minimum cash balance; dipping below triggers a penalty.",
  "debt", "debt")
T("dscr", "Debt service coverage (DSCR)", "finance",
  "Operating profit divided by loan payments: can the business's earnings cover its debt?",
  "Banks want it above about 1.25. Below 1 you are paying the loan out of savings.",
  "{company}'s DSCR right now: {dscr}.",
  "debt ebitda", "amortization ebitda")
T("rbf", "Revenue-based financing (RBF)", "finance",
  "An advance repaid as a fixed share of monthly revenue until a set total (e.g. 1.25x the advance) is paid back.",
  "No dilution and payments flex with revenue - good for companies with steady, high-margin recurring revenue. The implied interest can be high.",
  "An RBF offer to {company}: money now, then a % of each week's revenue until 1.25x is repaid.",
  "debt mrr gross_margin", "debt mrr")
T("venture_debt", "Venture debt", "finance",
  "Loans to VC-backed startups, given on the strength of their investors, usually right after an equity round.",
  "It extends runway with little dilution - but it is still debt, and it comes with warrants.",
  "Offered to {company} after a priced round: about 30% of the round size.",
  "warrant debt", "debt priced_round")
T("warrant", "Warrant", "finance",
  "A right to buy shares later at a fixed price, given to lenders as a sweetener.",
  "It is a small slice of dilution hiding inside a loan.",
  "Venture debt at {company} comes with warrants worth about 0.75% of the company.",
  "venture_debt dilution", "venture_debt")
T("revenue_multiple", "Revenue multiple", "finance",
  "Valuing a company as a multiple of its revenue (usually ARR). 8x ARR means $1M ARR -> $8M valuation.",
  "The multiple rises with growth rate, gross margin and retention - and swings with the market's mood.",
  "{arr} ARR at a multiple of {multiple}x gives about {valuation}.",
  "valuation arr", "arr valuation")
T("dcf", "DCF (discounted cash flow)", "finance",
  "Valuing a company as today's value of all the cash it will produce in the future, where money arriving later counts for less ('discounted') because of time and risk.",
  "It is the textbook method for mature companies. For startups the future is so uncertain that investors use multiples and comparables instead - but the logic (future cash, adjusted for risk) is the same.",
  "{company}'s valuation estimate uses an ARR multiple, not a DCF: its future cash flows are too uncertain to forecast credibly.",
  "valuation revenue_multiple", "revenue_multiple")
T("exit", "Exit", "finance",
  "The event that turns shares into money: selling the company (acquisition) or listing it on a stock exchange (IPO).",
  "Until an exit, your equity is paper. Investors need exits to return money to their own investors.",
  "An acquisition of {company} would be your exit.",
  "acquisition ipo waterfall", "equity")
T("acquisition", "Acquisition (M&A)", "finance",
  "One company buying another. M&A = mergers and acquisitions.",
  "Most successful startup outcomes are acquisitions, not IPOs. Companies are bought, not sold: acquirers come when you matter to their strategy.",
  "{bigcorp} could acquire {company} for its product, customers or team.",
  "loi acquihire exit due_diligence", "exit")
T("loi", "LOI (letter of intent)", "finance",
  "A mostly non-binding letter stating a buyer's intent to acquire and the headline terms, usually with an exclusivity period.",
  "The price in the LOI is the starting point: due diligence often brings it down ('retrading').",
  "An LOI for {company} arrives in the inbox; `mna` shows it.",
  "acquisition due_diligence", "acquisition due_diligence")
T("acquihire", "Acquihire", "finance",
  "An acquisition done mainly to hire the team; the product is often shut down.",
  "A soft landing for a company that didn't find product-market fit - usually small money, mostly for investors and as job offers.",
  "With weak revenue but a strong reputation, {company} might get an acquihire offer.",
  "acquisition", "acquisition")
T("waterfall", "Liquidation waterfall", "finance",
  "The order in which sale proceeds are paid out: lenders first, then preferred investors' preferences, then everyone by ownership.",
  "It decides what founders really receive. A $5M sale can mean very different founder outcomes depending on debt and preferences.",
  "If {company} were sold, loans ({loan_balance}) are repaid first, then investor preferences, then you get your share of the rest.",
  "liquidation_preference participating exit", "liquidation_preference acquisition")
T("earnout", "Earn-out", "finance",
  "Part of an acquisition price paid later, only if agreed targets are hit after the sale.",
  "It bridges disagreements on price - but you are betting on targets you no longer fully control.",
  "An acquirer may pay part of {company}'s price only if revenue targets are met the year after.",
  "acquisition loi", "loi")
T("ipo", "IPO (initial public offering)", "finance",
  "Selling a company's shares to the public on a stock exchange for the first time.",
  "The rarest exit: it needs scale (typically $100M+ revenue). It is why VCs care about TAM.",
  "{company} is a very long way from an IPO - but it is the outcome VC funds are built around.",
  "exit vc", "exit")
T("operating_leverage", "Operating leverage", "finance",
  "When revenue grows faster than costs because most costs are fixed.",
  "It is how software companies become extremely profitable at scale.",
  "Once {company} passes break-even, each new customer adds {arpu} of revenue but only {cogs} of cost.",
  "fixed_variable_costs gross_margin", "fixed_variable_costs break_even")
T("control", "Control", "vc",
  "Who gets to make the big decisions: selling the company, raising money, replacing the CEO.",
  "Founders can lose control long before they lose majority ownership - through board seats and investor rights.",
  "You own {founder_pct} of {company}; board seats granted: {board_seats}.",
  "board dilution", "board")

ORDER = list(TERMS)          # curriculum order = definition order above


def terms_in_tier(tier: int) -> list[Term]:
    return [t for t in TERMS.values() if t.tier == tier]


# ------------------------------------------------------------ going deeper
# Extra depth for terms where a definition is not enough: real-world
# benchmarks, common mistakes, and how professionals actually use them.
# Shown in the Notebook entry (`nb <term>`), not in the first pop-up.
DEEPER = {
    "problem": "Good problems are frequent (weekly, not yearly), painful (costs money, time or status) and already "
               "'solved' badly with a workaround - a spreadsheet, an intern, a habit. The workaround is your real "
               "competitor and your best evidence.",
    "customer_interview": "Rules of thumb from 'The Mom Test' (Rob Fitzpatrick): talk about their life, not your idea; ask "
                          "about specifics in the past, not generics or the future; talk less and listen more. Compliments "
                          "('great idea!') are noise. Commitments - time, money, an introduction - are signal.",
    "validation": "Strongest to weakest evidence: they pay (or pre-pay) > they give you time or introductions > they "
                  "describe the pain unprompted with a recent example > they say they would use it. Only the first "
                  "three count.",
    "mvp": "The 'minimum' is about scope, not quality: one job done well. Many famous products began as an MVP that "
           "was partly manual behind the scenes (a 'concierge' or 'Wizard of Oz' MVP) to test demand before building.",
    "pivot": "Common pivots: customer segment (same product, different buyer), problem (same customer, different pain), "
             "platform (a feature becomes the product), business model (e.g. B2C to B2B). Most pivots keep the team "
             "and what was learned - that is what separates a pivot from starting over.",
    "pricing": "Common models: flat subscription, per seat (per user), usage-based, tiered (good/better/best), freemium, "
               "transaction fee. Price to the VALUE the customer gets, not to your cost. A price increase that loses "
               "fewer than about 1 in 5 customers usually raises revenue.",
    "burn_rate": "Gross burn = everything you spend in a month. Net burn = gross burn minus revenue. When someone says "
                 "'burn' without qualification they usually mean net burn - ask if unsure.",
    "runway": "Founders usually plan 18-24 months of runway after a raise, start the next raise with 9-12 months left, "
              "and treat 6 months as an emergency. Recompute it every month: burn changes as you hire and grow.",
    "default_alive": "Term coined by Paul Graham (2015). The test: assume expenses stay as they are and revenue keeps "
                     "growing at the rate of the last few months - do you reach profitability before the money runs out?",
    "agent": "Typical agent tools: read and edit files, run shell commands, search the codebase, browse documentation. "
             "Good agents plan, act in small steps, run tests, and report. They fail by losing the thread in long "
             "tasks, guessing when context is missing, and claiming success without checking.",
    "spec": "Industry practice: write specs short (one page), concrete (examples, file paths, numbers) and testable. "
            "State constraints ('don't change the database schema') as clearly as goals. Many teams keep specs in "
            "the repository so humans and agents read the same document.",
    "context": "Context windows are large today (hundreds of thousands of tokens), but bigger is not better: models "
               "pay less attention to the middle of long contexts, and every token costs money. 'Context engineering' "
               "means giving the agent exactly the files and facts it needs - no more, no less.",
    "token": "Rough sizes: one token is about 4 characters of English; a page of text is about 500-700 tokens; code "
             "uses more tokens per line than prose. Output tokens usually cost several times more than input tokens.",
    "hallucination": "Common agent hallucinations: invented function names or library options, fake file paths, "
                     "claims that tests passed, made-up citations. Defences: run the code, run the tests, ask for "
                     "sources, and give the agent the real documentation in its context.",
    "code_review": "What reviewers look for: does it do what the spec says, are edge cases handled, are there tests, "
                   "is anything unsafe (secrets in code, unvalidated input), is it understandable. Reviewing agent "
                   "code is the same job - with extra suspicion of code that looks right but calls things that don't exist.",
    "tests": "Kinds: unit tests (one function), integration tests (parts together), end-to-end tests (the whole app "
             "like a user). A failing test that was written first and then made to pass ('test-driven development') "
             "is a strong way to give an agent an unambiguous target.",
    "tech_debt": "Debt is not always bad: shipping a quick version to learn whether customers want it is a good loan. "
                 "It becomes dangerous when nobody tracks it, nothing tests it, and every new feature is built on top.",
    "parallel_agents": "In practice teams run parallel agents in separate copies of the repository (git worktrees or "
                       "branches), each on an independent task, then merge one at a time - so conflicts surface at "
                       "merge, not silently.",
    "evals": "An eval is a dataset of inputs with known good outputs plus a way to score answers (exact match, a "
             "checklist, or another model grading). Run it on every prompt or model change, and track the score "
             "over time like any other KPI.",
    "churn": "Benchmarks (rough): consumer subscriptions often lose 5-10% of customers a month; small-business SaaS "
             "3-5%; enterprise SaaS under 1% a month. Also watch revenue churn, which can differ from customer "
             "churn when big and small customers leave at different rates.",
    "mrr": "MRR excludes one-off payments (setup fees, consulting). Founders track its parts: new MRR, expansion MRR, "
           "churned MRR and contraction MRR. Net new MRR = new + expansion - churned - contraction.",
    "cac": "'Blended' CAC divides all sales and marketing spend by all new customers; 'paid' CAC counts only "
           "customers from paid channels. Blended looks better because free customers lower it - investors will ask which one.",
    "ltv": "The simple formula assumes churn stays constant forever, which overstates LTV for young companies. Many "
           "investors cap the lifetime at 3-5 years or use measured cohort data instead.",
    "ltv_cac": "LTV:CAC of 3 is a rule of thumb, not a law. Investors also look at payback (how fast), because a high "
               "ratio with a 3-year payback can still starve a company of cash.",
    "gross_margin": "Rough benchmarks: classic SaaS 75-85%; AI-heavy products often 50-60% because of model costs; "
                    "marketplaces measure margin on their take, not on GMV; hardware 30-50%.",
    "pmf": "Sean Ellis's test: ask users 'How would you feel if you could no longer use this product?' If 40% or more "
           "answer 'very disappointed', you probably have product-market fit. Retention curves that flatten (instead "
           "of falling to zero) are the strongest quantitative sign.",
    "nrr": "Benchmarks (rough): below 90% is a leaky business; 100-110% is good; 120%+ is excellent and typical of "
           "the best enterprise software companies. Gross revenue retention (GRR) is the same but ignoring expansion, "
           "so it can never exceed 100%.",
    "tam": "Top-down TAM ('the education market is $7 trillion') impresses nobody. Bottom-up TAM - number of possible "
           "customers x what each would pay per year - shows you know who buys. Investors check that the math is "
           "yours, not a market-research headline.",
    "b2b": "In B2B the user, the buyer and the payer are often different people (the employee uses it, a manager "
           "chooses it, finance pays). Each needs a different argument.",
    "b2c": "Consumer businesses usually need a cheap, scalable channel - virality, content, app stores, or very "
           "efficient ads - because low prices leave little room for acquisition cost.",
    "sales_cycle": "Rough lengths: self-serve minutes; small business days to weeks; mid-market 1-3 months; enterprise "
                   "6-12 months. Longer cycles need more runway between first contact and first cash.",
    "moat": "Common moats: network effects, switching costs, economies of scale, brand, proprietary data, regulation "
            "or licences. 'We are better' or 'we are first' are not moats - they are head starts.",
    "equity": "Shares are usually split into common (founders, employees) and preferred (investors). A company can "
              "issue new shares at any time with board approval, which is why ownership percentages change.",
    "safe": "Created by Y Combinator in 2013. Since 2018 the standard is the 'post-money SAFE': the cap is measured "
            "after all SAFE money, which makes each SAFE's final percentage easy to compute (amount / cap) - and "
            "makes the dilution of stacking many SAFEs land entirely on the founders.",
    "valuation": "Early-stage valuations are set by supply and demand between investors and founders, anchored by "
                 "comparable deals, the team, traction and market mood - not by formulas. A higher valuation is not "
                 "always better: it raises the bar for the next round.",
    "dilution": "Typical dilution per round: pre-seed and seed 10-25%, Series A 15-25%, plus option-pool increases. "
                "Founders of companies that reach an IPO often own 10-20% in the end - and are happy, because the pie grew.",
    "cap_table": "Kept in a spreadsheet at first, later in cap-table software. Every SAFE, option grant and share "
                 "issue must be recorded; mistakes found during due diligence can delay or kill a round.",
    "term_sheet": "Key sections: economics (amount, valuation, option pool, liquidation preference, anti-dilution) and "
                  "control (board seats, protective provisions/vetoes, information rights). Most are standard; a "
                  "lawyer who does startup deals should read yours.",
    "liquidation_preference": "Market standard in most rounds: 1x non-participating. Preferences above 1x or "
                              "participation appear mainly in hard markets or troubled companies.",
    "option_pool": "Pool size is usually justified by a hiring plan: how much equity the next 12-24 months of hires "
                   "need. Negotiate it down to the plan; an oversized pool is pure dilution for you.",
    "vesting": "Standard: 4 years with a 1-year cliff, then monthly. 'Acceleration' clauses vest shares early on a "
               "sale ('single trigger') or on a sale plus being let go ('double trigger').",
    "board": "Early boards are often 3 seats: two founders and one investor, or one founder, one investor and one "
             "independent. The board approves budgets, option grants, new rounds and the sale of the company.",
    "burn_multiple": "Popularised by David Sacks (2020). Rough scale: under 1 amazing, 1-1.5 great, 1.5-2 good, "
                     "2-3 suspect, over 3 bad. It falls naturally as a company matures.",
    "income_statement": "The three statements: income statement (did we make a profit over the period?), balance "
                        "sheet (what do we own and owe at this moment?) and cash-flow statement (where did the cash "
                        "come from and go?). They are linked: profit flows into equity, cash appears on the balance sheet.",
    "cash_flow": "The cash-flow statement splits money into operating (running the business), investing (buying "
                 "equipment, acquisitions) and financing (loans, equity raised, repayments). A startup that is "
                 "cash-positive only because of financing is still burning.",
    "debt": "Lenders care about one thing: being repaid. They look at cash flow (can you pay?), collateral (what "
            "can they take?) and guarantees (who else pays?). Startups without revenue rarely qualify for bank debt "
            "without a personal guarantee.",
    "interest": "APR includes some fees and makes loans comparable; the effective cost of revenue-based financing or "
                "merchant cash advances can be far above their headline 'fee' once you account for how fast you repay.",
    "rbf": "Example: a $40k advance repaid at 1.25x means $50k total. Repaid within 12 months, that is roughly a 45%+ "
           "annualised cost; over 24 months, about 25%. Fast growth makes RBF more expensive, not cheaper.",
    "acquisition": "Common reasons to buy a startup: its revenue and customers, its technology, its team, or to remove "
                   "a competitor. Price is usually set as a multiple of revenue for strategic buyers - and can be much "
                   "higher when two buyers compete.",
    "waterfall": "Order in practice: transaction costs and debt first, then preferred stock (by seniority if rounds "
                 "differ), then common. Employees' unvested options may be cancelled, converted or accelerated "
                 "depending on the deal.",
    "due_diligence": "Typical requests: financial statements and bank records, customer contracts and churn data, the "
                     "cap table and all equity documents, code and security review, employment contracts and IP "
                     "assignment. Being organised early saves weeks.",
    "pitch_deck": "Classic order (variations of the Sequoia template): problem, solution, why now, market size, "
                  "competition, product, business model, traction, team, financials, the ask. 10-15 slides; "
                  "investors spend about 3 minutes on a deck they receive by email.",
    "accelerator": "The best known is Y Combinator (founded 2005). Typical terms: a fixed investment for a set "
                   "percentage (often 5-10%), three months of mentoring, and a demo day. The network often matters "
                   "more than the money.",
}
for _term_id, _text in DEEPER.items():
    TERMS[_term_id].deeper = _text
