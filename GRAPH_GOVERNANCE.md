# Graph Governance

Working reference for maintaining the impact graph. Covers ownership, quality rules, naming conventions, and the improvement cycle.

---

## 1. Source File Ownership

| File | Owns | Decision Rule |
|------|------|---------------|
| `universal_life_dependency_graph.yaml` | Consumer life categories (COICOP tree) | "Is it something a household directly interacts with?" |
| `employment_domain_graph.yaml` | Industries, companies, labor market | "Is it about where people work or earn?" |
| `financial_system_domain_graph.yaml` | Markets, monetary policy, banking, tax | "Is it a financial instrument, institution, or policy?" |
| `food_energy_graph.yaml` | Commodities, supply chains, agriculture | "Is it a commodity, crop, fuel, or production input?" |
| `local_governance_graph.yaml` | Municipal services, civic infrastructure | "Is it a city/state service, utility, or civic body?" |
| `edge_patches.yaml` | Cross-domain edges ONLY | "Does this edge connect nodes from different files?" |

When in doubt, apply the decision rule. If a node fits two files equally, prefer the one where it has the most causal edges.

---

## 2. Node Quality Checklist

Every node must satisfy all five checks before merging:

- [ ] **snake_case ID** matching `^[a-z][a-z0-9_]*$`
- [ ] **2+ aliases** (one human-readable name + one abbreviation minimum)
- [ ] **Category** from the canonical 15 (see below)
- [ ] **1+ causal edge** (not just `CONTAINS` or `IS_A` -- at least one `AFFECTS`, `PRODUCES`, `DISRUPTS`, etc.)
- [ ] **Edge descriptions non-empty** (every edge must have a description string)

---

## 3. Canonical Categories (15)

| Category | Description | Example Nodes |
|----------|-------------|---------------|
| `food_and_agriculture` | Food production, distribution, and pricing | `wheat`, `food_price_index`, `usda` |
| `energy` | Power generation, fuel, and energy markets | `crude_oil`, `electricity_grid`, `solar_pv` |
| `transport` | Movement of people and goods | `public_transit`, `freight_rail`, `fuel_cost` |
| `housing` | Shelter, rent, mortgages, construction | `rent_index`, `mortgage_rate`, `housing_starts` |
| `health_and_healthcare` | Medical services, insurance, public health | `health_insurance`, `hospital_capacity`, `drug_prices` |
| `education` | Schools, universities, student finance | `student_loans`, `public_schools`, `tuition_cost` |
| `employment_and_income` | Jobs, wages, labor market dynamics | `unemployment_rate`, `minimum_wage`, `tech_layoffs` |
| `financial` | Banking, investment, monetary instruments | `interest_rate`, `sp500`, `credit_score` |
| `governance_and_regulation` | Laws, agencies, policy decisions | `federal_reserve`, `epa`, `tariff_policy` |
| `environment_and_climate` | Climate, pollution, natural resources | `carbon_emissions`, `wildfire_risk`, `water_supply` |
| `consumer_goods` | Retail products and household spending | `grocery_prices`, `electronics`, `apparel` |
| `technology_and_telecom` | Digital infrastructure and communications | `broadband_access`, `cloud_computing`, `5g_network` |
| `infrastructure` | Physical systems -- roads, bridges, utilities | `power_grid`, `water_treatment`, `highway_system` |
| `demographics_and_social` | Population, migration, social dynamics | `population_growth`, `immigration_rate`, `birth_rate` |
| `global_economy` | International trade, forex, geopolitics | `trade_deficit`, `usd_exchange`, `opec_output` |

---

## 4. Canonical Edge Types (12)

| Edge Type | Description | Example |
|-----------|-------------|---------|
| `AFFECTS` | General causal influence (positive or negative) | `interest_rate` AFFECTS `mortgage_rate` |
| `PRODUCES` | Source creates or outputs the target | `refinery` PRODUCES `gasoline` |
| `REGULATES` | Authority controls or constrains the target | `epa` REGULATES `carbon_emissions` |
| `DISRUPTS` | Source interrupts or degrades the target | `drought` DISRUPTS `wheat` |
| `SUPPLIES` | Source provides input or material to target | `semiconductor_fab` SUPPLIES `electronics` |
| `DEPENDS_ON` | Target cannot function without source | `electric_vehicle` DEPENDS_ON `lithium` |
| `CONTAINS` | Hierarchical grouping (parent has child) | `food_and_agriculture` CONTAINS `wheat` |
| `IS_A` | Subtype relationship | `solar_pv` IS_A `renewable_energy` |
| `FUNDS` | Financial support or capital flow | `federal_budget` FUNDS `public_schools` |
| `COMPETES_WITH` | Rivalry or substitution relationship | `natural_gas` COMPETES_WITH `coal` |
| `EMPLOYS` | Source provides jobs in the target domain | `amazon` EMPLOYS `warehouse_workers` |
| `MANAGES` | Operational control or administration | `city_council` MANAGES `public_transit` |

---

## 5. Naming Conventions

| Element | Rule | Example |
|---------|------|---------|
| Node IDs | snake_case, `^[a-z][a-z0-9_]*$` | `crude_oil`, `sp500`, `public_transit` |
| Category names | Must be from the canonical 15 | `energy`, not `Energy` or `power` |
| Edge types | UPPER_SNAKE_CASE, from the canonical 12 | `DEPENDS_ON`, not `depends-on` or `DependsOn` |
| Aliases | At least 2 per node: human-readable name + common abbreviation | `["Crude Oil", "WTI"]`, `["S&P 500", "SPX"]` |

---

## 6. Deterministic Improvement Cycle

Run this cycle whenever the graph needs updating. Each step depends on the previous.

```
1. Run scorecard      python3 -m graph.quality --json > data/scorecard.json
2. Check gaps         python3 -m graph.coverage gaps
3. Prioritize         Pick gaps that affect the most users AND appear most in articles
4. Fix                python3 -m graph.admin add-node / lint / validate
5. Rebuild            python3 -m graph.merge
6. Verify             python3 -m graph.quality (compare with previous scorecard)
```

Do not skip step 6. If the scorecard regresses, revert the change and investigate.

---

## 7. Node Lifecycle

```
PROPOSED  -->  VALIDATED  -->  ACTIVE  -->  DEPRECATED  -->  REMOVED
```

| State | Meaning |
|-------|---------|
| **PROPOSED** | Node suggested but not yet reviewed. May lack edges or aliases. |
| **VALIDATED** | Passes the quality checklist. Ready for inclusion in the merged graph. |
| **ACTIVE** | Live in the merged graph. Used by the scoring pipeline. |
| **DEPRECATED** | Marked for removal. Still resolves in lookups but excluded from new scoring. |
| **REMOVED** | Deleted from all source files. Retained only in git history. |

Transition rules:
- PROPOSED -> VALIDATED: passes all 5 quality checks
- VALIDATED -> ACTIVE: included in a `graph.merge` run
- ACTIVE -> DEPRECATED: node is no longer relevant or has been superseded
- DEPRECATED -> REMOVED: after one release cycle with no regressions

---

## 8. Cross-File Overlap Rules

1. **A node must exist in exactly ONE source file.** No duplicates across files.
2. If a node is needed in multiple domains, place it in the most natural owner file (use the decision rules in Section 1) and create cross-domain edges in `edge_patches.yaml`.
3. Run `python3 -m graph.admin validate` to detect duplicates. Fix any violations before merging.

---

## 9. Edge Patch Guidelines

`edge_patches.yaml` exists solely for edges that connect nodes from different source files.

**Rules:**
- Only cross-domain edges belong here. Intra-file edges go in the source file.
- Every patch edge must include all five fields:
  - `type` -- from the canonical 12
  - `description` -- non-empty explanation of the relationship
  - `weight` -- float 0.0-1.0 indicating strength
  - `polarity` -- `positive` or `negative`
  - `delay` -- temporal lag (`immediate`, `days`, `weeks`, `months`, `quarters`, `years`)
- Run `python3 -m graph.admin lint` after adding or modifying patches.
- Review patches during every improvement cycle -- stale cross-domain edges are a common source of drift.
