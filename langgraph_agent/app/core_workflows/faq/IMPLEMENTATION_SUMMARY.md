# Workflow #3 (Tenant Support & FAQ) -- Implementation Summary

## What was built

A standalone, testable subgraph at `app/orchestrator/faq/`, following the exact
folder pattern already used by `app/orchestrator/maintenance/`:

```
faq/
  state.py            FAQState -- own TypedDict, isolated from MaintenanceState
  schemas.py           3 structured-output models (intent, groundedness, property slots)
  mcp_client.py         Connects to the existing property_search MCP server
  graph.py              The 8-node StateGraph + all conditional edges
  nodes/
    common.py            Shared LLM / Gemini / Pinecone clients, credentials from env only
    classify_intent_node.py
    rag_retrieve_node.py
    rag_generate_node.py
    collect_property_slots_node.py
    call_property_mcp_node.py
    recommend_generate_node.py
    clarify_node.py
    compose_response_node.py
  ingestion/
    config.py            Chunking + Pinecone constants
    ingest.py             CLI: loads .txt today, .pdf once the client provides real docs
  knowledge_base/
    sample_pet_policy.txt  Test document with 2 policies, section-headered
```

Also added: `langgraph_agent/test_faq_stage1.py` (test harness), `.env.example`
(placeholders, real `.env` untouched), `requirements-faq.txt` (new dependencies).

## How it follows the design doc

- **Two data sources, never blended** (section 1): `rag_retrieve_node` only ever
  touches Pinecone; `call_property_mcp_node` only ever touches the MCP server.
  Neither node calls the other's source.
- **4-way classification, 1 LLM call** (section 2.1): `classify_intent_node`,
  structured output, `Literal["KNOWLEDGE","PROPERTY","MIXED","UNCLEAR"]`.
- **Deterministic routing after classification** (section 7.3): every conditional
  edge in `graph.py` is a plain Python function reading state -- no LLM calls
  in the routing layer, same rule as maintenance's `priority_router`.
- **Confidence gate** (section 4): `rag_retrieve_node` checks similarity threshold
  (0.75) AND runs an LLM self-check (`GroundednessCheck`) before allowing
  `rag_generate_node` to run. Either check failing routes straight to escalation.
- **Citation** (section 4): every retrieved chunk carries `source` + `section`
  metadata from ingestion; `rag_generate_node`'s prompt requires citing it.
- **Zero-match handling, ranking, cap at 3-5** (section 5.3): implemented in
  `recommend_generate_node`.
- **Multi-turn slot accumulation** (section 7.4): `graph.py` compiles with a
  `MemorySaver` checkpointer keyed by `session_id` / `thread_id`, same pattern
  as maintenance -- new turns merge into existing `property_filters` rather
  than overwriting.

## Known gaps / follow-ups (not blockers for v1 testing)

1. ~~MCP schema mismatch (bedrooms not filterable).~~ **Closed.** The `bedrooms`
   column already existed in `elarion.db`, it just wasn't exposed as a filter.
   Added `bedrooms` as an optional parameter through `search_properties_db` ->
   `search_properties` MCP tool -> `call_property_mcp_node`, defaulting to
   `None` at every layer so the legacy voice-agent's `property_search_node.py`
   (which never passes it) is unaffected. `budget_min/budget_max` and
   `availability_only` from the design doc's section 5.1 were effectively
   already covered -- single `budget` maps to a max-price filter (matching the
   doc's own fallback rule), and the DB query already hardcodes
   `is_available = TRUE`. `session_id` for multi-turn continuity is handled at
   the graph/checkpointer level, not the MCP call itself, so no gap there
   either.
2. **Chunking is a first pass.** `ingestion/ingest.py` uses simple header
   detection + fixed word-window chunking, not the fuller semantic chunker
   implied by section 4. Good enough to validate the pipeline end to end;
   worth revisiting once real policy PDFs are in and you can see actual
   retrieval quality.
3. **This subgraph is not wired to the orchestrator yet.** Same status as
   maintenance -- it's fully callable on its own (`faq_graph.ainvoke(...)`),
   but the Layer 3 router that dispatches to it based on `intent` is still the
   next piece to build, as discussed.

## Before you run it

Only Test 2 (Property path) works with your current `.env` -- it just needs
the existing `GROQ_API_KEY` and the property search MCP server, both already
in place.

Test 1 (Knowledge path) needs two new keys added to `langgraph_agent/.env`
(see `.env.example` for the exact names):
- `GOOGLE_API_KEY` -- Gemini, for embeddings
- `PINECONE_API_KEY` -- Pinecone, for the vector index

Then install the two new packages:
```
pip install -r requirements-faq.txt --break-system-packages
```

Then ingest the sample document once (creates the Pinecone index automatically
on first run):
```
cd langgraph_agent
python -m app.orchestrator.faq.ingestion.ingest --file app/orchestrator/faq/knowledge_base/sample_pet_policy.txt
```

## How to test

```
cd langgraph_agent
python test_faq_stage1.py
```

**Test 1 -- Knowledge path.** Sends: *"What's the pet deposit if I want to
keep a cat?"*
Expected: `intent = KNOWLEDGE`, `confidence_score` above 0.75, `escalate =
False`, and a final response that states the PKR 15,000 pet deposit figure
with a citation like `(sample_pet_policy.txt - Section 2: Pet Deposit)`.

**Test 2 -- Property path, 2 turns.**
Turn 1 sends: *"Do you have any 2-bedroom apartments in Lahore?"* -- budget is
missing on purpose. Expected: `missing_property_fields = ["budget"]`, and the
agent asks *"What's your budget range?"* instead of calling the MCP server.
Turn 2 sends: *"My budget is around 120 lakhs."* -- same `thread_id`, so
`property_filters` should now show `location`, `property_type`, and `budget`
all merged together from both turns. Expected: `call_property_mcp` runs, and
the final response lists actual property matches from `elarion.db`, or the
"couldn't find any... want me to check a nearby area" message if there are no
matches in your seed data for that combination.

If either test's final response looks wrong, the `[State snapshot]` block
printed after each turn shows exactly which field diverged, so you can tell
me the turn number and field rather than pasting the whole transcript.
