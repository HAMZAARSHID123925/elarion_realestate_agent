# FAQ & Property Search Workflow Architecture

> **Document Path:** `docs/SDD/FAQ_Property_Search_Architecture.md`
> **Status:** Active Architectural Reference
> **Domain:** Knowledge Base FAQ & Property Listings Search

---

## 1. Domain Purpose

The **FAQ & Property Search Workflow** (`langgraph_agent/app/core_workflows/faq/`) provides intelligent, automated responses to tenant inquiries regarding building policies, lease rules, and available property listings using Retrieval-Augmented Generation (RAG) and Model Context Protocol (MCP) tools.

---

## 2. Workflow State & Nodes

### State Schema (`FAQState`)
* `messages`: Conversation history
* `user_query`: Raw inquiry text
* `rag_context`: Retrieved policy excerpts from vector store
* `property_filters`: Extracted search criteria (city, property_type, price range, bedrooms)
* `missing_property_fields`: Missing criteria needed for search refinement
* `final_response`: Generated response delivered to user
* `escalate`: Boolean flag when inquiry requires human staff assistance

### Node Flow & Graph Architecture
```text
                         [ Inbound Query ]
                                ↓
                     [ classify_faq_intent ]
                                ↓
                        Intent Classification
                          ├── General Policy / FAQ ──► [ retrieve_faq_context ] ──► [ generate_faq_answer ]
                          └── Property Search       ──► [ parse_property_query ] ──► [ mcp_property_search ]
                                                                                           ↓
                                                                                 [ format_search_results ]
                                                                                           ↓
                                                                                          END
```

---

## 3. Tool & Database Integration

1. **ChromaDB Vector Store**: Indexes markdown knowledge base files located in `knowledge_base/` for policy and procedure lookups.
2. **MCP Tool Server (`mcp_server.py`)**: Exposes property querying tools against PostgreSQL `properties` table (with indexed lookups on `city`, `property_type`, `price_lakhs`).
3. **Master Pipeline Integration**: Invoked via `app/department_nodes.py:run_faq` and clears `active_department` after answering single-turn queries.
