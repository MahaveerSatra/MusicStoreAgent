"""
SQL tools for the two sub-agents.

Account tools get customer_id from ToolRuntime context — the LLM never needs
to know or pass it, which eliminates any chance of cross-customer data leakage.

Music tools operate on the public catalog and require no auth scoping.
"""

import json
from dataclasses import dataclass

from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from database import run_query


@dataclass
class CustomerContext:
    """Runtime context injected per-invocation by the auth layer."""
    customer_id: int


# ---------------------------------------------------------------------------
# Sub-agent 1: Orders & Account tools
# ---------------------------------------------------------------------------

@tool
def get_customer_info(runtime: ToolRuntime[CustomerContext]) -> str:
    """Return profile information for the currently authenticated customer."""
    customer_id = runtime.context.customer_id
    rows = run_query(
        """
        SELECT CustomerId, FirstName, LastName, Email, Phone, Address, City, Country
        FROM Customer WHERE CustomerId = :cid
        """,
        {"cid": customer_id},
    )
    if not rows:
        return "No customer profile found."
    return json.dumps(rows[0], indent=2)


@tool
def get_order_history(runtime: ToolRuntime[CustomerContext]) -> str:
    """Return a list of past invoices (orders) for the authenticated customer."""
    customer_id = runtime.context.customer_id
    rows = run_query(
        """
        SELECT InvoiceId, InvoiceDate, BillingCountry, Total
        FROM Invoice
        WHERE CustomerId = :cid
        ORDER BY InvoiceDate DESC
        """,
        {"cid": customer_id},
    )
    if not rows:
        return "No orders found."
    return json.dumps(rows, indent=2)


@tool
def get_invoice_details(invoice_id: int, runtime: ToolRuntime[CustomerContext]) -> str:
    """
    Return the line-item details for a specific invoice.
    Ownership is verified automatically — the invoice must belong to the authenticated customer.
    """
    customer_id = runtime.context.customer_id
    ownership = run_query(
        "SELECT CustomerId FROM Invoice WHERE InvoiceId = :iid",
        {"iid": invoice_id},
    )
    if not ownership or ownership[0]["CustomerId"] != customer_id:
        return "Invoice not found or does not belong to your account."

    rows = run_query(
        """
        SELECT t.Name AS TrackName, ar.Name AS Artist,
               al.Title AS Album, il.UnitPrice, il.Quantity
        FROM InvoiceLine il
        JOIN Track t ON il.TrackId = t.TrackId
        JOIN Album al ON t.AlbumId = al.AlbumId
        JOIN Artist ar ON al.ArtistId = ar.ArtistId
        WHERE il.InvoiceId = :iid
        """,
        {"iid": invoice_id},
    )
    return json.dumps(rows, indent=2)


# ---------------------------------------------------------------------------
# Sub-agent 2: Music Discovery tools
# ---------------------------------------------------------------------------

@tool
def search_artists(name: str) -> str:
    """Search for artists by name. Supports partial matches."""
    rows = run_query(
        "SELECT ArtistId, Name FROM Artist WHERE Name LIKE :q LIMIT 10",
        {"q": f"%{name}%"},
    )
    if not rows:
        return f"No artists found matching '{name}'."
    return json.dumps(rows, indent=2)


@tool
def get_albums_by_artist(artist_id: int) -> str:
    """Return all albums for a given artist ID."""
    rows = run_query(
        """
        SELECT al.AlbumId, al.Title, ar.Name AS Artist
        FROM Album al JOIN Artist ar ON al.ArtistId = ar.ArtistId
        WHERE al.ArtistId = :aid ORDER BY al.Title
        """,
        {"aid": artist_id},
    )
    if not rows:
        return "No albums found for this artist."
    return json.dumps(rows, indent=2)


@tool
def get_tracks_by_album(album_id: int) -> str:
    """Return all tracks for a given album, including genre and duration in minutes."""
    rows = run_query(
        """
        SELECT t.Name AS Track, g.Name AS Genre,
               ROUND(t.Milliseconds / 60000.0, 2) AS DurationMinutes, t.UnitPrice
        FROM Track t
        JOIN Genre g ON t.GenreId = g.GenreId
        WHERE t.AlbumId = :aid ORDER BY t.TrackNumber
        """,
        {"aid": album_id},
    )
    if not rows:
        return "No tracks found for this album."
    return json.dumps(rows, indent=2)


@tool
def get_genre_recommendations(genre: str) -> str:
    """
    Return a sample of tracks in a given genre — useful for personalized recommendations.
    Genre examples: Rock, Jazz, Latin, Metal, Classical, Pop, Blues, Reggae.
    """
    rows = run_query(
        """
        SELECT t.Name AS Track, ar.Name AS Artist, al.Title AS Album,
               g.Name AS Genre, t.UnitPrice
        FROM Track t
        JOIN Album al ON t.AlbumId = al.AlbumId
        JOIN Artist ar ON al.ArtistId = ar.ArtistId
        JOIN Genre g ON t.GenreId = g.GenreId
        WHERE g.Name LIKE :q
        ORDER BY RANDOM() LIMIT 8
        """,
        {"q": f"%{genre}%"},
    )
    if not rows:
        return f"No tracks found in the '{genre}' genre."
    return json.dumps(rows, indent=2)


# Exported tool sets for sub-agent binding
ACCOUNT_TOOLS = [get_customer_info, get_order_history, get_invoice_details]
MUSIC_TOOLS = [search_artists, get_albums_by_artist, get_tracks_by_album, get_genre_recommendations]
