"""
Simulated multi-tenant authentication for the TuneDesk demo.

Uses LangGraph SDK Auth decorators — the same production pattern used with
Supabase JWT (see github.com/langchain-samples/lsd-custom-route-react-ui).

For the demo, token validation is replaced by a simple mock:
    Authorization: Bearer {customer_id}

In production, swap _validate_token() to decode a real JWT from Supabase
(or any OAuth provider) — nothing else in auth.py needs to change.
"""

from langgraph_sdk import Auth

# ---------------------------------------------------------------------------
# Mock customer registry
# ---------------------------------------------------------------------------

MOCK_CUSTOMERS = {
    "17": {"identity": "17", "name": "Jack Smith",    "email": "jacksmith@microsoft.com"},
    "24": {"identity": "24", "name": "Frank Ralston", "email": "fralston@gmail.com"},
    "57": {"identity": "57", "name": "Luis Rojas",    "email": "luisrojas@yahoo.cl"},
}


def _validate_token(authorization: str) -> dict | None:
    """
    Demo implementation: parse 'Bearer {customer_id}' and return user dict.
    Production implementation: decode & verify Supabase JWT here.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return MOCK_CUSTOMERS.get(token)


# ---------------------------------------------------------------------------
# Auth handler
# ---------------------------------------------------------------------------

auth = Auth()


@auth.authenticate
async def authenticate(authorization: str) -> Auth.types.MinimalUserDict:
    """Validate the Bearer token and return the user identity."""
    user = _validate_token(authorization)
    if not user:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Invalid or missing authorization token. Use 'Bearer {customer_id}'.",
        )
    return {
        "identity": user["identity"],
        "display_name": user["name"],
        "permissions": ["chat"],
    }


@auth.on.threads.create
async def on_thread_create(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.create.value,
):
    """Tag new threads with the owner's customer_id so they're filterable."""
    return {"owner": ctx.user.identity}


@auth.on.threads
async def on_threads_access(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.value,
):
    """Filter thread listings so customers only see their own threads."""
    return {"owner": ctx.user.identity}


@auth.on.runs
async def on_runs_access(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.runs.value,
):
    """Filter run listings so customers only see their own runs."""
    return {"owner": ctx.user.identity}
