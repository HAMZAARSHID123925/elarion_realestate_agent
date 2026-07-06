import re

with open("mcp_server.py", "r") as f:
    content = f.read()

# Replace import
content = content.replace("import psycopg\n", "import psycopg\nfrom psycopg_pool import AsyncConnectionPool\n")

# Replace _conn function with pool initialization
old_conn = """# ── DB helper: get a fresh async connection per call ─────────────────
async def _conn():
    return await psycopg.AsyncConnection.connect(DATABASE_URL)"""

new_conn = """# ── DB helper: Connection Pool ───────────────────────────────────────
pool = None

async def get_pool():
    global pool
    if pool is None:
        pool = AsyncConnectionPool(conninfo=DATABASE_URL, min_size=1, max_size=5, open=False)
        await pool.open()
    return pool"""

content = content.replace(old_conn, new_conn)

# Replace tool connection scopes
content = content.replace("async with await _conn() as conn:", "async with (await get_pool()).connection() as conn:")

# Fix the commit bug in create_ticket. Find where `await conn.commit()` is located and ensure it returns INSIDE the try/except but WITHOUT exiting the connection context and closing it prematurely if we want to return the result, OR just let the context close and return the result AFTER.
# Actually, since it's `async with ... as conn`, returning inside the block is fine.
# Wait, returning inside `async with` is correct and closes the connection gracefully.
# But `after_state` is computed before.
# Currently, it is:
#         await conn.commit()
# 
#         return json.dumps({"status": "success", "idempotent": False, "ticket": after_state})
# 
# The issue was that the `return` was OUTSIDE the `async with` but because `after_state` was defined inside, it was fine, but `conn.commit()` was ALSO outside the `async with` because of indentation!
# Let's fix the indentation of `conn.commit()` and `return`. We can just find that block and replace it.

old_commit_block = """            )

        await conn.commit()

        return json.dumps({"status": "success", "idempotent": False, "ticket": after_state})"""

new_commit_block = """            )

                await conn.commit()

            return json.dumps({"status": "success", "idempotent": False, "ticket": after_state})"""

content = content.replace(old_commit_block, new_commit_block)

# Wait, idempotency block also has `return json.dumps(...)` and `await conn.commit()`.
# Let's check idempotency check:
old_idem = """                await conn.commit()
                # Fetch full row to return
                await cur.execute(
                    "SELECT ticket_id, tenant_id, unit_id, category, urgency, status "
                    "FROM maintenance_tickets WHERE ticket_id = %s",
                    (ticket_id,),
                )
                row = await cur.fetchone()
                return json.dumps({"""

# Actually, the indentation in `create_ticket` inside `try` block was messed up by me earlier.
# The `try:` is at 4 spaces.
# `async with (await get_pool()).connection() as conn:` is at 8 spaces.
# `async with conn.cursor() as cur:` is at 12 spaces.
# So `await conn.commit()` should be at 12 spaces (inside the connection context, maybe after the cursor context).
# Let's just fix it properly.

with open("mcp_server.py", "w") as f:
    f.write(content)
print("Updated mcp_server.py")
