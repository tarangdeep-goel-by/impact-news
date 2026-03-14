"""Ask Gemini to evaluate the final graph constitution."""
import os

with open('.env') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# Read the full taxonomy file
with open('taxonomy/TAXONOMY.md') as f:
    taxonomy = f.read()

PROMPT = f"""You are reviewing the final version of a Graph Constitution for a causal knowledge graph. This is the document that will govern ALL graph construction for a news personalization engine focused on India.

This constitution was developed iteratively:
1. We proposed 11 rules
2. You (an earlier Gemini session) reviewed them and found issues
3. We incorporated your feedback: clarified covariation semantics, relaxed strict MECE, kept granularity parity but separated structure from scale via edge weights, kept One Node One Home but added secondary_tags, added edge conditionality, acyclicity enforcement, causal provenance, and a portal/port node system for cross-tree connections.

Here is the FINAL document. Please evaluate it as a complete, self-consistent system.

=== FULL TAXONOMY DOCUMENT ===
{taxonomy}
=== END DOCUMENT ===

Please evaluate:

1. **INTERNAL CONSISTENCY**: Do any of the 15 rules contradict each other? Are there edge cases where two rules give conflicting guidance?

2. **COMPLETENESS**: Is there anything a graph builder would encounter in practice that NO rule addresses? Specifically think about:
   - What happens when they are unsure about a classification?
   - What happens when they need to deprecate or rename a node?
   - What happens when new L1s are needed?

3. **STRESS TEST**: Apply ALL 15 rules to these 5 entities. For each entity, show which rules activate and what the outcome is:
   - Zomato (the company and the app)
   - Aadhaar (the system and the citizen's ID card)
   - Auto-rickshaw fare in Bangalore
   - Indian rupee depreciation
   - Work-from-home policy at TCS

4. **PHASE TRANSITION RISKS**: At each phase boundary (1a->1b, 1b->2a, 2a->2b, 2b->3, 3->4), what could go wrong? What validation should be run?

5. **OVERALL VERDICT**: Is this constitution ready to build against, or does it need more work? Rate it on a scale of 1-10 for:
   - Clarity (can a new contributor follow it?)
   - Completeness (does it cover enough?)
   - Practicality (can it actually be applied without constant judgment calls?)

Be ruthlessly honest. We would rather fix problems now than during construction."""

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
