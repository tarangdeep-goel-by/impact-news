# Impact News — Questionnaire & Progressive Profiling Design

> How to connect a user to 1,110 graph nodes across 21 domains with minimum friction.

**Created**: 2026-03-09
**Status**: Research Complete

---

## Table of Contents

1. [Research Findings](#1-research-findings)
2. [The Core Question Set](#2-the-core-question-set)
3. [Progressive Profiling Tiers](#3-progressive-profiling-tiers)
4. [Inference Engine](#4-inference-engine)
5. [Telegram Bot UX Design](#5-telegram-bot-ux-design)
6. [Privacy-First Profiling](#6-privacy-first-profiling)
7. [Event-Driven Profiling](#7-event-driven-profiling)
8. [Graph Coverage Analysis](#8-graph-coverage-analysis)

---

## 1. Research Findings

### 1.1 Form Completion & Drop-Off Data

| Metric | Finding | Source |
|--------|---------|-------|
| Optimal question count | 6-10 questions for >50% completion | SurveySparrow 2025 |
| Time threshold | <5 minutes; >12 min = 3x dropout | Survicate, YourCX |
| >12 questions | Completion drops below 50% | YourCX 2025 |
| >15 questions | 15-40% response rate drop | Zuko Conversion Stats |
| Sweet spot | 8-10 well-crafted questions | Clootrack 2025 |
| Form interaction → submit | 65.99% who start, complete | Zuko 2025 |
| One question per screen | Maximizes completion vs multi-question screens | Formsort, Amalgama |

**Key takeaway**: Our Tier 1 (3 questions) is well within safe limits. Total across all tiers should never exceed 15 explicitly asked questions — the rest should be inferred or event-driven.

### 1.2 Indian Fintech Onboarding Patterns

**Groww**: Progressive disclosure — minimal jargon, visually guided, account created in minutes. Asks for PAN + Aadhaar (regulatory), then uses Tartan's HyperVerify for unified PAN-UAN verification to auto-fill employment info. Investment profiling happens through usage, not questionnaires.

**Zerodha**: More deliberate — extra verification for derivatives/commodities. Two user archetypes (active traders vs long-term investors) get different flows. Intentionally slower for safety perception.

**Cred**: No KYC until financial services are used. Profile built from credit card data — zero explicit questions for core product. PAN/bank details only when user opts into Cred Mint (P2P lending).

**Jupiter/Fi**: Ask goal-based questions ("What are you saving for?") during onboarding, then use spending pattern analysis to build the rest of the profile automatically.

**Pattern**: Indian fintech apps ask 0-3 explicit profiling questions. Everything else is inferred from KYC documents, usage behavior, or financial account data.

### 1.3 Health App Onboarding Patterns

**HealthifyMe**: Onboarding asks age, height, weight, gender, fitness goal, dietary preference, and current fitness level (7 questions). Uses commitment bias — once users input goals, they're more likely to stick. Progress bar throughout.

**Practo**: Minimal profiling at signup. Health data collected at point of need (booking a consultation, ordering medicine). Progressive enrichment through usage.

**PharmEasy**: Prescription upload + address. No health questionnaire. Profile built from purchase history (medicines ordered = conditions inferred).

**Pattern**: Health apps split into two models — (1) goal-based upfront questionnaire (fitness apps), or (2) transaction-driven inference (pharmacy/consultation apps). The transaction model is more relevant for us.

### 1.4 Insurance Comparison Flows

**PolicyBazaar**: For health insurance: age, gender, city, existing diseases, family members to cover (5 inputs). For car insurance: registration number, city (2 inputs — rest auto-fetched from VAHAN database). For term life: age, gender, smoker status, income band, city (5 inputs). Always shows quotes immediately after the minimum viable set.

**Acko**: Direct-to-consumer. Car insurance: just vehicle registration number. Health: age, city, pre-existing conditions. Emphasis on speed — "quote in 30 seconds."

**Digit Insurance**: Custom modular card system — one requirement per screen. Reduced confusion vs traditional multi-field forms. Added space for explanations on each card.

**Pattern**: Insurance sites are masters of high-leverage questions. They ask the absolute minimum needed to segment risk, then show value (a quote) immediately. The gap between "give info" and "get value" is seconds, not minutes.

### 1.5 Making Long Questionnaires Feel Short

| Technique | How It Works | Example |
|-----------|-------------|---------|
| **Progress bar** | Visual completion indicator | Shine app: dot-style progress across screens |
| **Endowed progress** | Pre-check "done" items to create head start | Quora: shows 2/5 already done at start |
| **One question per screen** | Reduces cognitive load | Digit Insurance card system |
| **Immediate value after each answer** | Reward loop per question | PolicyBazaar: shows quote count updating |
| **Gamification** | Points, badges, streaks | Duolingo: demo lesson + gems before profile |
| **Chunking** | Group into themed sections | "About You" → "Your Work" → "Your Home" |
| **Smart defaults** | Pre-fill likely answers | City from IP, age range from phone model |
| **Skip always visible** | Reduces pressure, paradoxically increases completion | NN/g research on sensitive questions |

### 1.6 Conversational vs Form-Based

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Form-based** | Fast, familiar, accessible | Feels like paperwork, low engagement | Simple data (age, city) |
| **Conversational** | Engaging, higher quality data, feels natural | Slower, harder to skip around | Sensitive topics, complex branching |
| **Card swipe** | Fun, fast, binary choices | Limited to yes/no, loses nuance | Preference discovery, gamified profiling |
| **Hybrid** | Best of both — forms for structured data, conversation for context | More complex to build | Our use case |

**Cleo (budgeting app)** is the gold standard: chatbot interface walks through onboarding with casual, relatable questions, then responds with funny personalized feedback based on spending. Makes finance feel approachable.

**For Telegram**: Hybrid approach — inline keyboard buttons for structured choices (city, job sector), free text for specific answers (company name, dietary detail), and conversational framing around each question.

---

## 2. The Core Question Set

### Design Principle: Maximum Graph Activation Per Question

Each question is evaluated by how many graph nodes it can activate (directly or via inference). Questions are ordered by activation power.

### The 9 Core Questions (Priority Order)

#### Q1: "Which city do you live in?"
**Format**: Text with autocomplete (top 50 Indian cities as quick buttons)
**Time**: 3 seconds
**Graph activation**: ~180 nodes

| Domain | Nodes Activated | How |
|--------|----------------|-----|
| Local governance | Municipal corp, property tax, water supply, sewage, waste management | Direct: city → municipal body |
| Water systems | River basin, water source, water quality, water disputes | Inference: city → river system |
| Transport | Metro availability, bus system, traffic, road quality | Direct: city → transport infra |
| Utilities | Electricity board (BESCOM/MSEDCL/etc), tariff structure | Inference: city → state → utility provider |
| Environment | Air quality, flood risk, drought risk, heat stress | Inference: city → climate zone + pollution data |
| State policy | State budget, state taxes, state schemes | Inference: city → state → state policy nodes |
| Healthcare (local) | Government hospitals, health infrastructure | Inference: city → district health facilities |
| Education (local) | School boards, college cluster | Inference: city → education infra |
| Law & order | Crime rate, policing | Inference: city → safety data |
| Climate | Monsoon pattern, cyclone risk, flood zone | Inference: city → geo-climate data |
| Food | Regional staple crops, local food prices | Inference: city → agri-zone → crop pattern |
| Energy | Electricity provider, tariff slab, power cuts | Inference: city → state → DISCOM |

**Inference rules**:
- City → State → State government policies, budget, taxes
- City → Climate zone → Monsoon risk, drought risk, flood risk, heat stress
- City → DISCOM → Electricity tariff, power reliability
- City → Municipal corporation → Property tax, water tariff, waste management
- City → River basin → Water disputes, supply adequacy
- City → Tier (1/2/3) → Cost of living band, infrastructure quality
- City → Air quality index band → Pollution exposure

---

#### Q2: "What do you do for work?"
**Format**: Two-part — (a) job title free text, (b) sector picker (inline keyboard with 12 sectors)
**Time**: 8 seconds
**Graph activation**: ~150 nodes

Sector picker options:
```
IT/Software | Banking/Finance | Healthcare | Manufacturing
Education   | Government/PSU  | Retail      | Consulting
Startups    | Gig/Freelance   | Agriculture | Other
```

| Domain | Nodes Activated | How |
|--------|----------------|-----|
| Employment | Sector, sub-sector, employer type, automation risk, hiring trends | Direct from sector + title |
| Financial | Income band, tax bracket, PF/NPS eligibility | Inference: sector + title → salary band |
| Insurance | Group health insurance likelihood, life cover adequacy | Inference: employer type → benefits |
| Education | Skill relevance, upskilling needs | Inference: sector → technology disruption risk |
| Gig economy | Platform dependency (if gig/freelance) | Direct if selected |

**Inference rules**:
- Sector + Title → Income band (using PayScale/Glassdoor distributions)
- Sector → Automation/AI displacement risk score
- Sector → Cyclicality (IT = US economy dependent, Agriculture = monsoon dependent)
- "IT/Software" → IT services sector nodes (TCS, Infosys, Wipro, etc. as potential employers)
- "Banking/Finance" → BFSI sector nodes, RBI regulation sensitivity
- "Government/PSU" → 7th Pay Commission, DA hike, pension rules
- "Gig/Freelance" → Platform economy nodes, labor law changes, GST for freelancers
- Title seniority → Income refinement (intern < analyst < manager < director < VP)

---

#### Q3: "Do you own or rent your home?"
**Format**: 3 buttons: `Own (with loan)` | `Own (no loan)` | `Rent`
**Time**: 2 seconds
**Graph activation**: ~60 nodes

| Domain | Nodes Activated | How |
|--------|----------------|-----|
| Financial | Mortgage/home loan, EMI, interest rate sensitivity, property tax | Direct if "Own (with loan)" |
| Housing | Rent control, rent inflation, landlord dependency | Direct if "Rent" |
| Real estate | Property value, RERA, stamp duty | Direct if "Own" |
| Insurance | Home insurance relevance | Inference: own → insurable asset |
| Tax | HRA exemption (rent) vs Home loan tax benefit (own) | Direct |
| Local governance | Property tax node | Direct if "Own" |

**Inference rules**:
- Own (with loan) → Floating rate likely → RBI repo rate sensitivity HIGH
- Own (with loan) + City → Approximate EMI range
- Rent + City → Approximate rent range, rent control applicability
- Own (no loan) → Property tax exposure, low interest rate sensitivity
- Own → Stamp duty, registration, RERA nodes activated
- Rent → HRA tax benefit, rental agreement, deposit nodes activated

---

#### Q4: "How do you get around daily?"
**Format**: Multi-select inline keyboard: `Own car` | `Own bike/scooter` | `Metro/train` | `Bus` | `Auto/cab` | `Cycle/walk` | `WFH mostly`
**Time**: 3 seconds
**Graph activation**: ~70 nodes

| Domain | Nodes Activated | How |
|--------|----------------|-----|
| Energy | Petrol/diesel prices, fuel subsidy, EV charging | Direct from vehicle type |
| Transport | Metro fare, bus fare, toll roads, parking | Direct from mode |
| Environment | Carbon footprint, pollution exposure | Inference from mode |
| Financial | Auto loan, auto insurance, fuel budget | Inference if own car/bike |
| Employment | Commute cost, WFH infrastructure | Direct from mode/WFH |

**Inference rules**:
- Own car → Petrol/diesel price sensitivity, auto insurance, toll roads, parking costs
- Own car + City → Approximate fuel spend (distance estimates by city)
- Own bike → Petrol sensitivity (lower magnitude), helmet/safety regulations
- Metro/train → Fare hike sensitivity, route disruption, infrastructure investment impact
- Auto/cab → Ride-hailing platform dependency (Uber/Ola), surge pricing
- WFH → Electricity cost sensitivity UP, commute cost sensitivity ZERO, broadband dependency UP
- Multi-select "car + metro" → Hybrid commuter, moderate fuel sensitivity

---

#### Q5: "Do you have any active loans?"
**Format**: Multi-select: `Home loan` | `Car loan` | `Education loan` | `Personal loan` | `Credit card debt` | `No loans`
**Time**: 3 seconds
**Graph activation**: ~40 nodes

| Domain | Nodes Activated | How |
|--------|----------------|-----|
| Financial | Interest rate nodes (repo rate, MCLR, EBLR), EMI, debt-to-income | Direct per loan type |
| Banking | Bank lending rates, NPA, credit score | Inference |
| Monetary policy | RBI rate decisions, MPC meetings | HIGH relevance if floating rate loans |
| Insurance | Loan protection insurance | Inference |

**Inference rules**:
- Home loan → EBLR/MCLR sensitivity (highest impact of any loan type), RBI MPC = push notification trigger
- Car loan → Fixed rate likely, lower rate sensitivity, asset depreciation
- Education loan → Moratorium rules, tax benefit (Section 80E), interest subsidy schemes
- Personal loan → Highest rate sensitivity (14-24% range), unsecured lending regulation
- Credit card debt → Highest interest exposure (36-42%), RBI credit card regulation
- No loans → Low interest rate sensitivity, savings yield becomes more relevant
- Multiple loans → Compound rate sensitivity, debt-to-income stress indicator

---

#### Q6: "Do you invest in any of these?"
**Format**: Multi-select: `Stocks` | `Mutual Funds` | `Fixed Deposits` | `Gold` | `PPF/NPS` | `Crypto` | `Real Estate` | `Don't invest`
**Time**: 3 seconds
**Graph activation**: ~80 nodes

| Domain | Nodes Activated | How |
|--------|----------------|-----|
| Financial | Equity markets, MF categories, FD rates, gold prices, crypto regulation | Direct per selection |
| Tax | Capital gains tax, LTCG, STCG, STT | Inference per asset class |
| Regulation | SEBI, RBI (for FD/debt), crypto regulation | Direct |
| Global macro | US markets, Fed rates (if stocks/MF) | Inference |

**Inference rules**:
- Stocks → SEBI regulation, market volatility, capital gains tax, brokerage
- Stocks + Sector(IT) → Likely holds IT sector stocks, NASDAQ correlation
- Mutual Funds → AMC regulation, expense ratio changes, SIP flows, AMFI data
- Fixed Deposits → Bank FD rates, RBI rate sensitivity (inverse to loans), tax on interest
- Gold → Gold prices, import duty, sovereign gold bonds, gold ETFs
- PPF/NPS → Government scheme changes, EEE tax status, lock-in rules
- Crypto → Crypto regulation (ban/allow), 30% tax, TDS, exchange risk
- Real Estate → RERA, property prices, rental yield, stamp duty
- Don't invest → Financial literacy content opportunity, savings account rate relevance

---

#### Q7: "Any dietary preferences or restrictions?"
**Format**: Multi-select: `Vegetarian` | `Vegan` | `Non-vegetarian` | `Eggetarian` | `Gluten-free` | `Lactose-intolerant` | `No restrictions`
**Time**: 3 seconds
**Graph activation**: ~50 nodes

| Domain | Nodes Activated | How |
|--------|----------------|-----|
| Food | Specific food category nodes (dairy, meat, grains, pulses) | Direct per diet |
| Agriculture | Crop-specific price sensitivity | Inference |
| Health | Nutritional deficiency risk, supplement needs | Inference |

**Inference rules**:
- Vegetarian → Pulse prices (dal = primary protein), dairy prices, cooking oil prices HIGH; meat prices ZERO
- Vegetarian + City(South India) → Rice prices > wheat prices
- Non-vegetarian → Poultry prices, fish prices, meat inflation nodes activated
- Vegan → Pulse/legume prices HIGH, dairy prices ZERO, plant-based alternatives
- Gluten-free → Wheat/bread ZERO impact, rice/millet prices HIGH, specialty food costs
- Lactose-intolerant → Dairy prices LOW impact, alternative milk prices
- No restrictions → All food category nodes active at baseline weights

---

#### Q8: "Do you have family dependents?"
**Format**: Multi-select: `Spouse/partner` | `Children (school-age)` | `Children (college)` | `Elderly parents` | `None`
**Time**: 3 seconds
**Graph activation**: ~60 nodes

| Domain | Nodes Activated | How |
|--------|----------------|-----|
| Education | School fees, college fees, education loans, board exam changes | Direct if children |
| Healthcare | Elderly care, chronic disease management, health insurance | Direct if elderly parents |
| Insurance | Life insurance need, health insurance family floater | Inference |
| Financial | Household budget multiplier, savings rate | Inference |
| Employment | Spouse income (dual income?), single earner pressure | Inference |

**Inference rules**:
- Spouse → Dual income household (reduces individual financial vulnerability), joint filing options
- Children (school) → School fee inflation, education policy changes, CBSE/ICSE/state board changes, tuition costs
- Children (college) → Higher education costs, education loan sensitivity, abroad education (forex), entrance exam policies
- Elderly parents → Geriatric healthcare costs, medication prices, elderly care infrastructure, Section 80D deduction
- Multiple dependents → Higher insurance need, higher expense sensitivity, lower savings buffer
- None → Lower insurance need, higher discretionary spending, higher investment capacity

---

#### Q9: "Any chronic health conditions in your household?"
**Format**: Multi-select: `Diabetes` | `Heart condition` | `Asthma/respiratory` | `Thyroid` | `Blood pressure` | `Mental health` | `None` | `Prefer not to say`
**Time**: 3 seconds
**Graph activation**: ~40 nodes

| Domain | Nodes Activated | How |
|--------|----------------|-----|
| Healthcare | Specific medication nodes, treatment protocols | Direct per condition |
| Pharma | Drug pricing, generic availability, NPPA price control | Direct |
| Insurance | Pre-existing disease exclusions, premium loading | Direct |
| Food | Dietary constraints from health (sugar-free, low-sodium) | Inference |
| Air quality | Respiratory sensitivity | Direct if asthma |

**Inference rules**:
- Diabetes → Insulin prices, glucose monitoring devices, sugar-free foods, HbA1c testing, metformin supply
- Heart condition → Statin prices, cardiac stent regulation, health insurance premium, cardiac hospital accessibility
- Asthma/respiratory → Air quality index = push notification trigger, inhaler prices, pollution regulation
- Thyroid → Thyroid medication (levothyroxine), endocrinology appointments
- Blood pressure → Antihypertensive medication prices, salt regulation, lifestyle impact
- Mental health → Mental healthcare accessibility, therapy costs, workplace mental health policy
- Prefer not to say → Skip gracefully, attempt inference from other signals later
- None → Preventive health content, wellness nodes at low priority

---

### The 9 Questions Ranked by Graph Activation

| # | Question | Activation | Time | Cumulative Coverage |
|---|----------|-----------|------|-------------------|
| Q1 | City | ~180 nodes | 3s | ~16% |
| Q2 | Work | ~150 nodes | 8s | ~30% |
| Q3 | Own/Rent | ~60 nodes | 2s | ~35% |
| Q4 | Commute | ~70 nodes | 3s | ~41% |
| Q5 | Loans | ~40 nodes | 3s | ~45% |
| Q6 | Investments | ~80 nodes | 3s | ~52% |
| Q7 | Diet | ~50 nodes | 3s | ~57% |
| Q8 | Dependents | ~60 nodes | 3s | ~62% |
| Q9 | Health | ~40 nodes | 3s | ~65% |

**Total explicit ask time**: ~31 seconds for 9 questions
**Graph coverage**: ~65% from 9 questions + inference
**Remaining 35%**: Filled by event-driven profiling (Tier 2) + behavioral inference

### Additional High-Leverage Questions (Tier 1.5 — ask if user is engaged)

| Question | Format | Activation | Use When |
|----------|--------|-----------|----------|
| "What's your approximate age range?" | Buttons: 18-25, 26-35, 36-45, 46-55, 55+ | ~30 nodes | Refines income, health, life stage inference |
| "Do you have health insurance?" | Yes (employer) / Yes (self) / No | ~25 nodes | Insurance gap analysis, out-of-pocket risk |
| "Do you or family live abroad?" | Yes (I do) / Yes (family) / No | ~20 nodes | Forex, immigration, remittance nodes |
| "Do you run a business?" | Yes / Side hustle / No | ~30 nodes | GST, business regulation, MSME schemes |
| "What's your primary cooking fuel?" | LPG / PNG / Electric / Other | ~15 nodes | Energy subsidy, LPG price sensitivity |
| "Do you have a domestic helper?" | Yes / No | ~10 nodes | Minimum wage, labor law, domestic worker regulation |

---

## 3. Progressive Profiling Tiers

### Tier 0 — Zero Input (Immediate Value)
**Trigger**: User opens bot for the first time
**Questions asked**: 0
**Data collected**: IP geolocation (city estimate), device language, Telegram profile info
**Graph coverage**: ~5% (city-level defaults)

**What we show**: "Here are stories affecting people in [detected city] today."

**Value proposition**: Demonstrate the product works BEFORE asking for anything.

**Inference**:
- IP → City (80% accuracy for mobile)
- Language → Regional preference, likely state
- Telegram profile → Name (can sometimes infer gender, community)

---

### Tier 1 — The Big 3 (30 seconds)
**Trigger**: After user sees 2-3 stories from Tier 0 and engages (clicks, reacts)
**Questions asked**: 3 (City, Work, Own/Rent)
**Graph coverage**: ~35%

**Framing**: "Want stories that actually affect YOUR life? Three quick questions."

**Flow**:
```
Bot: "I can personalize this for you. Takes 30 seconds. Ready?"
     [Let's go] [Maybe later]

Bot: "Where do you live?"
     [Mumbai] [Delhi] [Bangalore] [Chennai] [Hyderabad] [Pune] [Other ⌨️]

Bot: "What sector do you work in?"
     [IT/Software] [Banking/Finance] [Healthcare] [Manufacturing]
     [Education] [Government] [Retail] [Startups] [Other ⌨️]

     "And your job title?" (free text)

Bot: "Do you own or rent your home?"
     [Own (with loan)] [Own (no loan)] [Rent]

Bot: "Done! Here's what's affecting you today..."
     [Shows 3 personalized impact stories immediately]
```

**Critical UX rule**: Show personalized stories IMMEDIATELY after the 3rd answer. The gap between "give data" and "see value" must be zero.

---

### Tier 1.5 — The Quick 6 (60 seconds more)
**Trigger**: User has been active for 2+ days and engaged with 3+ stories
**Questions asked**: 6 more (Commute, Loans, Investments, Diet, Dependents, Health)
**Cumulative graph coverage**: ~65%

**Framing**: "Your feed is good, but I can make it great. 6 more questions — takes 60 seconds."

**Flow**: Same one-question-per-screen pattern with inline keyboards. Show a dot-style progress bar (●●●○○○).

**Endowed progress trick**: Show "You're already 40% profiled!" when starting (because Tier 1 data exists).

---

### Tier 2 — Event-Driven Profiling (Ongoing)
**Trigger**: A news event creates a natural opportunity to ask
**Questions asked**: 1 at a time, max 2-3 per week
**Cumulative graph coverage**: 65% → 80% over 4-6 weeks

**Design principle**: Every question demonstrates value. The question IS the content.

See [Section 7: Event-Driven Profiling](#7-event-driven-profiling) for full design.

---

### Tier 3 — Periodic Check-Ins (Monthly)
**Trigger**: 30 days since last profile update OR major life event signals
**Questions asked**: 1-3 contextual questions
**Cumulative graph coverage**: 80% → 85% (maintenance + refinement)

**Format**:
```
Bot: "Quick monthly check-in! Has anything changed?"
     [New job] [Moved cities] [New family member] [New investment]
     [Started/stopped medication] [Nothing changed ✓]
```

If user selects something, ask 1-2 follow-up questions specific to that change. If "Nothing changed" — done in 1 tap.

---

### Tier 4 — Deep Profiling (Opt-In)
**Trigger**: User explicitly requests deeper analysis OR is a power user (30+ days active)
**Methods**: Account Aggregator (India), manual deep questionnaire, document upload
**Cumulative graph coverage**: 85% → 95%

**Account Aggregator flow** (India-specific):
- User consents via AA framework
- System reads bank statements, mutual fund holdings, insurance policies
- Auto-maps to exact graph nodes (specific stocks, specific insurance products, exact EMI amounts)

**Manual deep profiling** (for users who don't want AA):
- Specific company name (not just sector)
- Exact loan amount and rate type
- Specific mutual fund names
- Specific medications
- Family members' cities

---

## 4. Inference Engine

### 4.1 What Can Be Inferred from City + Job Title + Age in India

Given just these 3 data points, we can build a surprisingly complete profile:

#### From City Alone

| City | Inferences |
|------|-----------|
| Mumbai | MCGM municipal body, BMC water supply, Western/Central/Harbour railway lines, BEST buses, Metro Line 1/2A/7, Brihanmumbai power supply (Tata/Adani/BEST), coastal flooding risk, high cost of living, MMRDA infrastructure, Maharashtra state policy, Marathi + Hindi + English |
| Bangalore | BBMP municipal body, BWSSB water (Cauvery sourced), BMTC buses, Namma Metro, BESCOM electricity, lake flooding risk, moderate cost of living, Karnataka state policy, Kannada + Hindi + English, tech hub (IT sector likely) |
| Delhi | MCD/NDMC, DJB water (Yamuna sourced), Delhi Metro, DTC buses, BSES/TPDDL electricity, severe air pollution (winter), high cost of living, Delhi state + central government overlap |

**Inference accuracy by city tier**:
- Tier 1 (Metro): 70-80% accuracy on lifestyle inferences
- Tier 2 (State capitals, large cities): 60-70% accuracy
- Tier 3+ (Small cities/towns): 50-60% accuracy (more variance)

#### From Job Title + Sector

| Sector + Title | Inferences |
|----------------|-----------|
| IT/Software + "Software Engineer" | Income: 8-25 LPA, employer likely IT services or product company, US market dependency, automation-aware, likely has health insurance, stock/ESOP possible, remote work likely |
| Banking + "Manager" | Income: 10-20 LPA, PSU or private bank, regulated sector, PF + gratuity, job stability high, rate sensitivity aware |
| Government + "IAS/IPS/IFS" | Income: 6-15 LPA + perks, 7th Pay Commission, DA hikes, government housing possible, pension eligible, high job security |
| Startups + "Founder" | Income: 0-50+ LPA (high variance), ESOP/equity heavy, GST registered likely, angel tax, startup India benefits, high risk |
| Gig/Freelance + "Delivery" | Income: 2-4 LPA, platform dependent (Zomato/Swiggy/Zepto), no health insurance, no PF, labor law changes critical |

#### From Age Range

| Age | Inferences |
|-----|-----------|
| 18-25 | Early career, likely renting, low investment, education loans possible, parents as dependents unlikely, high digital adoption |
| 26-35 | Mid-career, first home loan likely, starting investments (SIP boom), marriage/children transitions, peak career mobility |
| 36-45 | Established career, likely homeowner, school-age children, portfolio diversification, health consciousness rising |
| 46-55 | Senior career, college-age children, retirement planning, health conditions emerging, property wealth |
| 55+ | Pre/post-retirement, NPS/EPF withdrawal, fixed-income preference, healthcare heavy, elderly care might be needed for self |

#### Combined Inference Accuracy

| # of Answers | Coverage | Accuracy | What's Known Well | What's Still Guessed |
|-------------|----------|----------|-------------------|---------------------|
| 3 (city + work + own/rent) | ~35% | 60-75% | Location infra, sector exposure, housing cost structure | Income (band only), investments, health, family |
| 5 (+ commute + loans) | ~45% | 70-80% | + Transport costs, interest rate sensitivity | Investments, diet, health, family |
| 9 (all core) | ~65% | 80-90% | Most major life dependencies | Specific employer, exact amounts, niche conditions |
| 15 (+ Tier 1.5) | ~75% | 85-92% | Nearly complete profile | Specific products, exact financial details |
| Event-driven (after 4-6 weeks) | ~80% | 88-95% | Verified through news-context questions | Deep financial specifics, rare conditions |

### 4.2 Public Data Sources for Profile Enrichment

| Source | What It Provides | Legal Status |
|--------|-----------------|-------------|
| EPFO (via UAN) | Employer name, PF contribution (= salary indicator) | Requires user consent (AA framework) |
| VAHAN database | Vehicle registration → make, model, fuel type, age | Public for insurance, requires reg number |
| Property registration | Property value, stamp duty paid, loan details | State-specific, semi-public |
| LinkedIn (public profile) | Job title, company, education, connections | Public data, scraping TOS issues |
| Glassdoor/AmbitionBox | Salary ranges by company + title | Public aggregate data |
| CIBIL (via consent) | Credit score, loan details, credit card limits | Requires explicit user consent |
| RBI CRILC | Large loan exposure (>5 Cr) | Not consumer-facing |
| MCA21 (company registry) | Company details, directors, financials | Public |
| NSE/BSE | If user shares demat, exact holdings | Requires AA consent |

**Privacy-first approach**: We do NOT scrape or access any of these without explicit consent. We use publicly known distributions (median salary for IT engineer in Bangalore = X) for inference, not individual data.

---

## 5. Telegram Bot UX Design

### 5.1 Bot Personality

**Tone**: Informed friend, not a robo-surveyor. Think "smart colleague who reads the news for you."

**Language**: English with Hindi/regional terms where natural ("Your dal prices might go up" not "Pulse commodity prices face upward pressure").

**Name suggestion**: "Impact" or "Asar" (Hindi for impact/effect)

### 5.2 Conversation Patterns

#### First Interaction (Tier 0)
```
User: /start

Bot: Hey! I'm Impact — I find news that actually affects your life.
     Not clickbait. Not opinions. Just stuff that hits your wallet,
     your commute, or your family.

     Here's what's happening in your area today:

     📰 RBI keeps repo rate unchanged at 6.5%
     → Affects: Home loan EMIs, FD rates, savings
     Impact: Neutral (no change for now)

     📰 Tomato prices up 40% in wholesale markets
     → Affects: Grocery bills in North India
     Impact: ₹200-400/month extra for a family of 4

     Want me to find stories that affect YOU specifically?
     [Yes, personalize →] [Just browse]
```

#### Tier 1 Flow
```
Bot: Great! 3 quick taps and I'll know what matters to you.
     ① ② ③

     Where do you live?

     [Mumbai] [Delhi NCR] [Bangalore] [Hyderabad]
     [Chennai] [Pune] [Kolkata] [Ahmedabad]
     [Type another city ⌨️]
```

User taps: [Bangalore]

```
Bot: Bangalore — got it! 🏙

     What sector do you work in?

     [IT/Software] [Banking/Finance] [Healthcare]
     [Manufacturing] [Education] [Government/PSU]
     [Retail/Commerce] [Startups] [Gig/Freelance]
     [Other ⌨️]
```

User taps: [IT/Software]

```
Bot: And what's your role? (just type it)
```

User types: "Senior Software Engineer"

```
Bot: Last one — do you own or rent?

     [Own (with loan)] [Own (no loan)] [Rent]
```

User taps: [Rent]

```
Bot: Done! Here's your personalized feed:

     🔴 HIGH IMPACT
     Bangalore BESCOM announces 15% tariff hike
     → Your electricity bill goes up ~₹300-500/month
     → Affects: All Bangalore residents, especially renters
        (landlords often pass through utility hikes)

     🟡 MEDIUM IMPACT
     TCS and Infosys pause lateral hiring in Q3
     → IT sector hiring slowdown. No immediate risk for
        senior roles, but watch for project reallocation.

     🟢 LOW IMPACT
     Karnataka state budget allocates ₹5,000 Cr for metro expansion
     → Long-term commute improvement for Bangalore
     → Phase 3 likely operational by 2029

     I'll send you a daily digest at 8 AM. High-impact alerts come instantly.
     [Customize alerts ⚙️] [Ask me more questions →]
```

### 5.3 Inline Keyboard Design Rules

1. **Max 4 buttons per row** (wider buttons are easier to tap on mobile)
2. **Max 3 rows of buttons** before it feels overwhelming (12 buttons total)
3. **Always include a text input option** ("Other ⌨️" or "Type your answer")
4. **Use emoji sparingly** — one per button max, only when it aids recognition
5. **Button text under 20 characters** (truncation on small screens)
6. **Callback data under 64 bytes** (Telegram API limit)

### 5.4 Multi-Select Pattern

For questions like loans and investments where users need to select multiple options:

```
Bot: What do you invest in? (tap all that apply, then hit Done)

     [Stocks ✓] [Mutual Funds] [Fixed Deposits]
     [Gold] [PPF/NPS] [Crypto]
     [Real Estate] [Don't invest]

     [✅ Done]
```

When user taps an option, toggle the checkmark and update the keyboard. Final "Done" button submits.

### 5.5 Progress Indicator

Use message text, not a separate message:

```
Bot: Great! Question 2 of 3 — almost there!
     ● ● ○

     What sector do you work in?
```

### 5.6 Skip Handling

Every non-essential question should have a skip:

```
Bot: Any chronic health conditions in your household?

     [Diabetes] [Heart] [Asthma] [BP] [Thyroid]
     [Mental health] [None]
     [Skip — I'd rather not say]
```

If skipped, acknowledge gracefully:
```
Bot: No problem! I can still personalize based on what I know.
     I might ask about this later if a health-related story comes up
     that could be relevant.
```

---

## 6. Privacy-First Profiling

### 6.1 Principles

1. **Ask less, infer more**: If we can reasonably infer something from data the user already gave us, don't ask.
2. **Ranges over exact values**: Never ask for exact salary, exact loan amount, or exact age. Ranges give us enough for graph mapping.
3. **Skip is always an option**: No question should be mandatory except city (Tier 1).
4. **Explain why before asking**: Every sensitive question gets a one-line reason.
5. **Local storage, never uploaded**: Make this clear at onboarding and every time a sensitive question is asked.

### 6.2 Sensitive Question Framing

#### Income (NEVER ask directly)
Instead, infer from sector + title + city. If we must refine:
```
Bot: The government just changed tax slabs. To show you the impact,
     which bracket are you in?

     [Under 5L] [5-10L] [10-15L] [15-25L] [25L+]
     [Skip]
```
**Why this works**: The question is framed around a news event, not data collection. The user sees immediate value (tax impact) for sharing the info.

#### Health Conditions
```
Bot: Drug pricing regulator (NPPA) just capped prices on 40 diabetes
     medications. Does this affect anyone in your household?

     [Yes, someone has diabetes] [No] [Skip]
```
**Why this works**: News-triggered, shows immediate relevance, binary answer.

#### Debt/Loans
```
Bot: RBI just hiked the repo rate by 25 bps. This affects floating
     rate loans. Do you have any?

     [Yes, home loan] [Yes, other loan] [No floating rate loans] [Skip]
```

### 6.3 Trust-Building Messaging

**At onboarding** (show once):
```
Bot: A quick note on privacy:

     • Your answers stay on YOUR device only
     • I never upload your personal data to any server
     • I fetch news + analysis (same for everyone)
     • Your phone matches it to your profile locally
     • You can delete everything anytime: /deletedata

     [Got it →]
```

**At first sensitive question** (show once):
```
Bot: Just so you know — this info stays on your phone.
     I need it to find relevant stories, not to sell anything.
     You can always skip or delete later.
```

**Periodically** (once a month in digest):
```
Your data: 42 profile points stored locally on your device.
None uploaded to our servers. [View/Edit] [Delete All]
```

### 6.4 When to Ask vs When to Infer

| Data Point | Ask or Infer? | Rationale |
|-----------|--------------|-----------|
| City | ASK | Too important to guess wrong, easy to answer |
| State | INFER from city | 1:1 mapping |
| Climate zone | INFER from city | Deterministic |
| Income | INFER from sector + title + city | Sensitive, inference is good enough |
| Exact salary | NEVER ASK | Too sensitive, ranges sufficient |
| Employer name | ASK (Tier 4 only) | Useful but not essential for initial profiling |
| Loan existence | ASK | Binary/multiple choice, not sensitive |
| Exact loan amount | NEVER ASK | Infer range from city + own/rent |
| Health conditions | ASK (with skip option) | Cannot be reliably inferred, high-value for personalization |
| Dietary preference | ASK | Cannot be inferred, culturally sensitive to assume |
| Age | INFER from career stage, or ASK as range | Semi-sensitive in some contexts |
| Gender | NEVER ASK | Not needed for graph mapping, politically sensitive |
| Religion/caste | NEVER ASK | Not needed, highly sensitive |
| Political affiliation | NEVER ASK | Not needed, creates bias |

---

## 7. Event-Driven Profiling

### 7.1 Design Principle

Every event-driven question must satisfy the **Value-First Rule**:

```
1. Deliver the news insight FIRST
2. Show why it might be relevant
3. THEN ask if it applies to the user
4. User's answer = profiling data + demonstrates value
```

The user should feel they're getting smarter about the world, not filling out a form.

### 7.2 Event-Driven Question Templates

#### Pattern: Policy Change → Personal Applicability

```
📰 RBI raises repo rate by 25 basis points to 6.75%

This means floating rate home loans will see EMI increases
of ₹500-2,000/month depending on the loan amount.

Does this affect you?
[Yes, I have a home loan] [No home loan] [Skip]
```

**Graph nodes unlocked**: home_loan, floating_rate, eblr, rbi_mpc, repo_rate

---

#### Pattern: Price Change → Consumption Check

```
📰 Crude oil crosses $95/barrel — highest in 18 months

Petrol may increase ₹3-5/litre over the next 2 weeks.

How does this affect your commute?
[I drive daily] [Occasional driver] [Public transport/WFH] [Skip]
```

**Graph nodes unlocked**: crude_oil, petrol_price, commute_mode, fuel_cost

---

#### Pattern: Sector News → Employment Check

```
📰 Major US banks cut IT outsourcing budgets by 15%

This could affect hiring at Indian IT services companies
(TCS, Infosys, Wipro, HCL).

Is this relevant to your work?
[I work in IT services] [Different IT sector] [Not in IT] [Skip]
```

**Graph nodes unlocked**: it_services_sector, it_services_us_client, employer sub-sector refinement

---

#### Pattern: Regulatory Change → Financial Product Check

```
📰 SEBI mandates new risk disclosure for small-cap mutual funds

Small-cap MF investors will see additional risk warnings
and possible portfolio rebalancing.

Do you invest in small-cap mutual funds?
[Yes] [I invest in other MFs] [Don't invest in MFs] [Skip]
```

**Graph nodes unlocked**: mutual_funds, small_cap_mf, sebi_regulation

---

#### Pattern: Weather Event → Location + Asset Check

```
📰 IMD warns of heavy rainfall in Mumbai — red alert for 48 hours

Flood risk areas: Andheri, Dadar, Sion, Kurla.
Likely metro/train disruptions.

Are you in an affected area?
[Yes, I live there] [Yes, I commute through] [No, different area] [Skip]
```

**Graph nodes unlocked**: flood_risk, specific_neighborhood, commute_route, weather_vulnerability

---

#### Pattern: Tax Change → Filing Relevance

```
📰 New tax regime now default from FY 2025-26

If you haven't made a choice, you're automatically on the new regime.
This changes HRA, 80C, and home loan deductions.

Which tax regime do you follow?
[Old regime] [New regime] [Not sure] [Skip]
```

**Graph nodes unlocked**: tax_regime, hra_exemption, section_80c, home_loan_tax_benefit

---

### 7.3 Frequency & Fatigue Management

| Rule | Limit | Rationale |
|------|-------|-----------|
| Max event-driven questions per day | 1 | More feels like a survey |
| Max per week | 3 | Respects user attention |
| Min gap between questions | 8 hours | No morning + evening questions |
| Skip streak threshold | 3 skips in a row → pause for 2 weeks | User is signaling fatigue |
| Duplicate topic cooldown | Same domain: 14 days minimum | Don't ask about loans twice in a week |
| High-impact bypass | Score > 0.8 can ask even if at weekly limit | Truly important events override limits |

### 7.4 Question Timing

| Time | Good For | Bad For |
|------|----------|---------|
| 8-9 AM (with daily digest) | Work/finance questions, morning routine | Health, personal life |
| 12-1 PM (lunch break) | Food, lifestyle questions | Finance, work |
| 6-8 PM (commute/wind-down) | Commute, local governance, general | Nothing specific — most flexible |
| Weekend morning | Family, lifestyle, health | Work, finance (feels intrusive) |

### 7.5 Measuring Event-Driven Profiling Effectiveness

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Response rate to event-driven questions | >60% | Responses / (Questions sent - Skips) |
| Graph coverage increase per week | +2-3% | New nodes activated / Total nodes |
| Time to 80% coverage | 4-6 weeks | From Tier 1 completion |
| User perception | "I learn from these questions" not "Stop asking me" | Monthly micro-survey (1 question) |
| Skip rate | <30% | Skips / Questions shown |

---

## 8. Graph Coverage Analysis

### 8.1 Node Coverage by Domain and Tier

Based on 1,110 total nodes across 4 domain graphs + the universal life dependency graph:

| Domain | Total Nodes | Tier 0 | Tier 1 (3 Qs) | Tier 1.5 (9 Qs) | Tier 2 (Event) | Tier 4 (Deep) |
|--------|------------|--------|--------------|----------------|----------------|--------------|
| Food & Energy | 322 | 5% | 15% | 40% (diet + commute fuel) | 60% | 85% |
| Local Governance | 330 | 10% (city) | 35% (city + own/rent) | 45% (+ commute) | 65% | 80% |
| Employment | 226 | 0% | 30% (sector + title) | 35% (+ dependents) | 55% | 85% |
| Financial System | 232 | 0% | 15% (own/rent) | 50% (+ loans + invest) | 70% | 90% |
| **Total** | **1,110** | **~5%** | **~25%** | **~43%** | **~63%** | **~85%** |

*Note: Inference multiplier applied — each explicit answer activates 3-5x more nodes through inference chains.*

### 8.2 Coverage Curves

```
Coverage %
100 |                                                        ___------
 90 |                                                  ___--
 80 |                                            ___--
 70 |                                      ___--
 60 |                                ___--
 50 |                          ___--
 40 |                    ___--
 30 |              ___--
 20 |        ___--
 10 |  ___--
  0 |--
    +----+----+----+----+----+----+----+----+----+----+----
    0    1    3    5    9   12   15   20   30   50  100
              Questions asked (explicit + event-driven)

Key inflection points:
- 3 questions  → 25% (biggest ROI per question)
- 9 questions  → 43% (still high ROI, diminishing)
- 15 questions → 55% (explicit questions plateau)
- 30 (incl. event-driven) → 75% (event-driven high ROI)
- 50 (incl. deep + AA) → 85% (deep profiling)
- 100% → Requires continuous profiling + account aggregator
```

### 8.3 The Minimum Viable Question Set

If we could only ask **5 questions** and never ask again, the optimal set is:

1. **City** (activates local governance, utilities, climate, water, transport)
2. **Job sector + title** (activates employment, income inference, sector exposure)
3. **Own/Rent + loan status** (combined: activates housing, financial, interest rate sensitivity)
4. **Commute mode** (activates energy/fuel, transport, environment)
5. **Investments** (activates financial markets, tax, regulation)

These 5 cover the highest-activation nodes across all 4 domain graphs. Diet, dependents, and health are important but have lower cross-domain activation — they're deep within single domains rather than bridging multiple.

### 8.4 The "20% of Questions for 80% of Value" Analysis

The Pareto set is roughly:
- **3 questions** (city, work, own/rent) → **~60% of all high-impact alerts** the system could generate
- **9 questions** (full Tier 1.5) → **~80% of all high-impact alerts**
- **Beyond 9 questions** → diminishing returns, niche domain coverage

This is because high-impact events (rate hikes, fuel prices, major layoffs, food inflation) are covered by the macro profile (location + sector + housing + financial exposure). The long tail of niche events (specific medication price caps, specific school board changes) requires the deep profile from Tier 2+.

---

## Appendix A: Full Question → Node Mapping Table

| Q# | Question | Direct Nodes | Inferred Nodes | Key Domain Graphs |
|----|----------|-------------|----------------|-------------------|
| Q1 | City | municipal_corp, water_supply, metro_system, bus_system | DISCOM, climate_zone, river_basin, air_quality, cost_of_living, state_policy | local_governance, food_energy |
| Q2 | Work sector + title | sector node, sub-sector nodes | income_band, tax_bracket, employer_type, automation_risk, hiring_trends | employment |
| Q3 | Own/Rent | home_loan OR rent_node | EMI, property_tax, HRA, stamp_duty, RERA | financial_system, local_governance |
| Q4 | Commute | transport_mode nodes | fuel_cost, fare_hike, toll_road, parking, EV_charging | food_energy, local_governance |
| Q5 | Loans | specific loan type nodes | interest_rate_sensitivity, EBLR, MCLR, RBI_MPC | financial_system |
| Q6 | Investments | asset_class nodes | SEBI, capital_gains_tax, market_volatility, FD_rates | financial_system |
| Q7 | Diet | food_category nodes | specific_crop_prices, import_dependency, food_inflation | food_energy |
| Q8 | Dependents | dependent_type nodes | education_costs, elderly_care, insurance_need, household_budget | employment, financial_system, local_governance |
| Q9 | Health | condition nodes | medication nodes, pharma_regulation, insurance_premium, air_quality_sensitivity | food_energy (pharma), financial_system (insurance) |

## Appendix B: Research Sources

- [Progressive Profiling 101 — Descope](https://www.descope.com/learn/post/progressive-profiling)
- [Progressive Profiling — Typeform](https://www.typeform.com/blog/progressive-profiling-collect-better-data)
- [User Onboarding Best Practices — Formbricks](https://formbricks.com/blog/user-onboarding-best-practices)
- [Top 6 Fintech Onboarding Journeys — Setu](https://blog.setu.co/articles/top-6-fintech-onboarding-journeys)
- [Groww KYC — HyperVerge](https://hyperverge.co/blog/how-to-activate-kyc-in-groww-app/)
- [Zerodha Kite Onboarding Teardown — Medium](https://shubhambrnw.medium.com/zerodha-kite-onboarding-teardown-535c4568a985)
- [Psychology Behind Fitness App Onboarding — Amalgama](https://amalgama.co/the-psychology-behind-fitness-apps-onboarding/)
- [Weight Loss Onboarding Form — Formsort](https://formsort.com/article/weight-loss-onboarding-form/)
- [Onboarding Questionnaire for Finance App — Medium](https://medium.com/@harshiknayak/designing-onboarding-questionnaire-for-a-personal-finance-strategy-app-ux-case-study-0dcbfeb6b2bc)
- [Digit Insurance UX Design — Opposite HQ](https://oppositehq.com/portfolio/digit-insurance-user-experience/)
- [Survey Response Rate Benchmarks 2025 — SurveySparrow](https://surveysparrow.com/blog/survey-response-rate-benchmarks/)
- [25 Conversion Rate Statistics 2025 — Zuko](https://www.zuko.io/blog/25-conversion-rate-statistics-you-need)
- [Survey Completion Rate Study — Survicate](https://survicate.com/blog/survey-completion-rate/)
- [Research Effectiveness: Survey Completion — YourCX](https://yourcx.io/en/blog/2025/03/research-effectiveness-survey-questions-completion-rate/)
- [Handling Sensitive Questions — NN/g](https://www.nngroup.com/articles/sensitive-questions/)
- [How to Ask Sensitive Survey Questions — Qualtrics](https://www.qualtrics.com/blog/how-to-get-the-truth-when-asking-survey-questions-about-sensitive-topics/)
- [Income Survey Questions — SurveyMonkey](https://www.surveymonkey.com/learn/survey-best-practices/how-to-ask-income-survey-questions/)
- [Privacy and Sensitive Questions — Oxford Academic](https://academic.oup.com/poq/article/83/S1/169/5525026)
- [Telegram Inline Keyboard UX Guide](https://wyu-telegram.com/blogs/444/)
- [Multiselection Inline Keyboards in Telegram — Medium](https://medium.com/@moraneus/enhancing-user-engagement-with-multiselection-inline-keyboards-in-telegram-bots-7cea9a371b8d)
- [Onboarding Gamification Examples — StriveCloud](https://www.strivecloud.io/blog/gamification-examples-onboarding)
- [Gamify User Onboarding — Chameleon](https://www.chameleon.io/blog/gamify-user-onboarding)
- [Contextual Surveys with AI — Coforge](https://www.coforge.com/what-we-know/blog/elevating-feedback-gathering-contextual-surveys-with-ai)
- [User Modeling and Profiling Survey — arXiv](https://arxiv.org/html/2402.09660v2)
- [Average Salary in India 2026 — ClearTax](https://cleartax.in/s/average-salary-in-india)
- [Salary by City in India — SalaryExpert](https://www.salaryexpert.com/salary/browse/cities/all/india)
- [UX of Questions in User Onboarding — Chargebee](https://www.chargebee.com/blog/user-onboarding-questions/)
- [200 Onboarding Flows Study — DesignerUp](https://designerup.co/blog/i-studied-the-ux-ui-of-over-200-onboarding-flows-heres-everything-i-learned/)
