"""Ask Gemini to review the graph constitution."""
import os
import sys

with open('.env') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

PROMPT = """I am building a causal knowledge graph for a news personalization engine focused on India. The system delivers news articles to users based on how world events causally affect their personal life.

We have a taxonomy with two types of L1 categories:
- 5 TRIGGER L1s (system layer): Natural & Planetary, Institutional & Sovereign, Macro & Global Markets, Tech & Physical Infrastructure, Social/Demographic/Cultural
- 11 IMPACT L1s (citizen layer): Food, Housing, Transport, Livelihood, Finance, Health, Education, Safety, Environment, Digital, Leisure

We plan to build the graph in phases using an elevator model:
Phase 1a: Impact vertical trees (L1-L2-L3, CONTAINS/IS_A only)
Phase 1b: Impact lateral edges (AFFECTS, DISRUPTS, SUPPLIES, DEPENDS_ON between Impact nodes)
Phase 2a: Trigger vertical trees
Phase 2b: Trigger lateral edges
Phase 3: Bridge edges (Trigger to Impact via port nodes)
Phase 4: End-to-end validation

Here are 11 proposed constitution rules. Critically review each.

RULE 1: ENTITY PRINCIPLE - Nodes are entities not events. crude_oil yes, crude_oil_price_hike no.

RULE 2: TRIGGER/IMPACT CLASSIFICATION - Locus of Interface Test. Citizen directly experiences it? Yes=Impact, No=Trigger. Impacts can cause other impacts. The split is about nature not position in chain.

RULE 3: LEAF NODE TEST - Must be Matchable (LLM extracts from headline), Mappable (user profile connects), Edgeable (has causal edge not just IS_A/CONTAINS).

RULE 4: VERTICAL EDGE SEMANTICS - CONTAINS for taxonomy levels (L1>L2>L3). IS_A for specialization. Never mix.

RULE 5: DUAL-NATURE PREVENTION - Node is Trigger OR Impact never both. If entity has both faces, split into two nodes (crude_oil T3 vs retail_diesel I3). Bridge edge connects them.

RULE 6: PORT NODE CONVENTION - Boundary nodes tagged port:true for future bridges. Marks where Trigger-to-Impact bridges will land.

RULE 7: SIBLING DISTINCTNESS (MECE) - Same-level siblings mutually exclusive, collectively exhaustive. Test: Can a news article affect node A without affecting node B?

RULE 8: GRANULARITY PARITY - Leaf nodes within each L1 at roughly same granularity. No retail_tomato alongside vegetables.

RULE 9: INDIA-FIRST SCOPING - Every leaf passes: Would this appear in an Indian news headline in 2026?

RULE 10: ONE NODE ONE HOME - Each node in exactly one L1 tree. No duplicates across files.

RULE 11: EDGE COMPLETENESS - Every lateral edge needs: type (from 12 canonical), weight(0-1), polarity(+/-1), delay(IMMEDIATE/SHORT_TERM/MEDIUM_TERM/LONG_TERM), description.

Please:
1) Rate each rule (Strong/Needs refinement/Weak)
2) Identify GAPS - rules we need but dont have
3) Identify CONFLICTS between rules
4) Stress-test with 3 tricky Indian entities and show how rules handle them or fail
5) Suggest modifications"""

models = ['gemini-3.1-pro-preview', 'gemini-3-pro-preview', 'gemini-2.5-flash']
for model in models:
    print(f"Trying {model}...", flush=True)
    try:
        response = client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=16000)
            ),
            contents=PROMPT
        )
        print(f"SUCCESS with {model}\n", flush=True)
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'thought') and part.thought:
                    print('=== GEMINI THINKING ===', flush=True)
                    print(part.text, flush=True)
                    print('=== END THINKING ===\n', flush=True)
                elif part.text:
                    print(part.text, flush=True)
        break
    except Exception as e:
        print(f"FAILED ({type(e).__name__}): {e}\n", flush=True)
        continue
