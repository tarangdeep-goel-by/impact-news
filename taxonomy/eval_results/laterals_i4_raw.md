# I4 Lateral Edges — Gemini 3.1 Pro

<details><summary>Thinking (4086 chars)</summary>

**Intra-L1 Edge Generation: My Thought Process**

Alright, let's break this down systematically. The core goal is to generate causal edges *within* the "Livelihood & Employment" (I4) tree, specifically focusing on how different aspects within this domain influence each other. No inter-domain stuff, strictly within I4.

First, I need to thoroughly understand the structure. I've got this L1: I4, and then nested L2s, L3s, and L4s. Think *within* this tree. No reaching outside. I need to treat each node as a potential source *and* target. The key is to see the *flow* of causality.

Okay, I'm thinking about causal relationships. So, what drives what? Let's start with some key connections I see:

*   **MGNREGA/Farm Labor:** MGNREGA wages act as a rural wage floor. If MGNREGA wages increase, farm labor wages *have* to follow to compete for workers. It's a direct connection. Higher MGNREGA payouts establish a higher reservation wage in rural areas.

*   **Minimum Wage/Construction:** Minimum wages, of course, affect wages. Minimum wage directly influences wages in construction and manual labor. As minimum wage goes up, those rates follow.

*   **Unemployment/Gig Economy:** A high urban unemployment rate fuels the gig economy. But not in a good way for gig workers. It creates an oversupply of labor and pushes payouts down. That supply side pressure is important, I think I'll model this one.

*   **Startup/Layoffs/Unemployment:** Startup layoffs directly influence urban unemployment rates.

*   **Startup/Gig funding:** Startups are a major source of funding for the gig economy, particularly ride-hailing and delivery services.

*   **MSME/Manufacturing:** Healthy MSMEs lead to more factory jobs. It's a clear relationship.

*   **IT/Unemployment:** IT sector job growth *directly* reduces urban unemployment by absorbing engineering graduates, among other functions.

Now, let's be strict about the rules. It's about generating edges *according* to the rules, in YAML format, so I will ensure that my edges conform to the format requested.

Okay, YAML time, with some clear logic behind each edge. The key here is not just *what* affects what, but *how*. I'm also going to clarify my descriptions.

*   **Targeting Logic:** I need to make sure I am targeting the *correct* level in the tree. Target L3 by default; L4 only when a *specific* L4 node is affected, not the entire L3.

Here is the YAML:

```yaml
edges:
  - from: mgnrega_wages
    to: agriculture_and_allied
    type: AFFECTS
    weight: 0.8
    polarity: 1
    delay: SHORT_TERM
    description: "Higher MGNREGA payouts establish a higher reservation wage in rural areas, forcing private agricultural employers to raise daily farm labor wages to attract workers."
  - from: minimum_wage
    to: construction_and_manual
    type: AFFECTS
    weight: 0.7
    polarity: 1
    delay: MEDIUM_TERM
    description: "Upward revisions in statutory minimum wages establish a higher legal pay floor, pushing up daily wage rates for construction and manual building site labor."
  - from: urban_unemployment_rate
    to: delivery_and_logistics
    type: AFFECTS
    weight: 0.7
    polarity: -1
    delay: SHORT_TERM
    description: "High urban joblessness creates an oversupply of willing gig workers, allowing platform aggregators to reduce per-delivery payouts and incentive structures."
  - from: startup_ecosystem
    to: delivery_and_logistics
    type: FUNDS
    weight: 0.9
    polarity: 1
    delay: IMMEDIATE
    description: "Venture capital injected into the startup ecosystem directly finances the cash burn required to subsidize payouts for food delivery and quick commerce gig workers."
  - from: msme_manufacturing
    to: manufacturing_and_core
    type: PRODUCES
    weight: 0.8
    polarity: 1
    delay: MEDIUM_TERM
    description: "Growth and capacity expansion in small-scale MSME industries directly generate new shop floor roles and industrial jobs for factory workers."
  - from: startup_layoffs
    to: urban_unemployment_rate
    type: PRODUCES
    weight: 0.5
    polarity: 1
    delay:

</details>

## Response

```yaml
```yaml
- from: mgnrega_wages
  to: agriculture_and_allied
  type: AFFECTS
  weight: 0.8
  polarity: 1
  delay: SHORT_TERM
  description: "Higher MGNREGA payouts establish a higher reservation wage in rural areas, forcing private agricultural employers to raise daily farm labor wages to attract workers."

- from: minimum_wage
  to: construction_and_manual
  type: AFFECTS
  weight: 0.7
  polarity: 1
  delay: MEDIUM_TERM
  description: "Upward revisions in statutory minimum wages establish a higher legal pay floor, pushing up daily wage rates for construction and manual building site labor."

- from: urban_unemployment_rate
  to: delivery_and_logistics
  type: AFFECTS
  weight: 0.7
  polarity: -1
  delay: SHORT_TERM
  description: "High urban joblessness creates an oversupply of willing gig workers, allowing platform aggregators to reduce per-delivery payouts and incentive structures."

- from: startup_ecosystem
  to: delivery_and_logistics
  type: FUNDS
  weight: 0.9
  polarity: 1
  delay: IMMEDIATE
  description: "Venture capital injected into the startup ecosystem directly finances the cash burn required to subsidize payouts for food delivery and quick commerce gig workers."

- from: msme_manufacturing
  to: manufacturing_and_core
  type: PRODUCES
  weight: 0.8
  polarity: 1
  delay: MEDIUM_TERM
  description: "Growth and capacity expansion in small-scale MSME industries directly generate new shop floor roles and industrial jobs for factory workers."

- from: startup_layoffs
  to: urban_unemployment_rate
  type: PRODUCES
  weight: 0.5
  polarity: 1
  delay: IMMEDIATE
  description: "Mass downsizing and role eliminations in venture-backed tech companies directly add to the pool of unemployed white-collar professionals in urban centers."

- from: mgnrega_wages
  to: construction_and_manual
  type: AFFECTS
  weight: 0.6
  polarity: 1
  delay: MEDIUM_TERM
  description: "Attractive MGNREGA wages reduce distress migration from villages to cities, tightening the urban manual labor supply and forcing builders to offer higher construction wages."

- from: minimum_wage
  to: msme_manufacturing
  type: AFFECTS
  weight: 0.7
  polarity: -1
  delay: SHORT_TERM
  description: "Mandatory increases in base legal pay directly inflate labor costs for small-scale industries, squeezing the profit margins and income of SME factory owners."

- from: startup_layoffs
  to: freelance_and_services
  type: SUPPLIES
  weight: 0.6
  polarity: 1
  delay: SHORT_TERM
  description: "Tech sector downsizing pushes displaced software engineers and digital professionals into the gig economy, increasing the supply of freelance and independent platform workers."

- from: it_sector_jobs
  to: urban_unemployment_rate
  type: AFFECTS
  weight: 0.6
  polarity: -1
  delay: SHORT_TERM
  description: "Mass recruitment drives by major IT services firms absorb hundreds of thousands of engineering graduates, significantly reducing urban youth joblessness."

- from: startup_ecosystem
  to: ride_hailing
  type: FUNDS
  weight: 0.8
  polarity: 1
  delay: IMMEDIATE
  description: "Venture capital backing allows mobility startups to heavily subsidize driver earnings and offer lucrative incentives to cab and auto drivers on their platforms."

- from: maternity_leave_benefits
  to: manufacturing_and_core
  type: AFFECTS
  weight: 0.4
  polarity: -1
  delay: MEDIUM_TERM
  description: "Strict mandates requiring employers to fully fund extended maternity leave can inadvertently disincentivize the hiring of female factory workers in cost-sensitive industrial sectors."

- from: working_hours
  to: urban_unemployment_rate
  type: AFFECTS
  weight: 0.5
  polarity: 1
  delay: MEDIUM_TERM
  description: "Increases in mandatory shift timings and average working hours per employee reduce the total headcount required by corporations, marginally increasing urban unemployment."
```
```
