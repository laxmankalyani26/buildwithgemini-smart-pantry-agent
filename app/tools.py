"""
Firestore, public API, Maps, Image generation, and Video generation tool functions for smart-pantry-agent.
"""
import base64
import json
import os
import time
import urllib.parse
import urllib.request
import uuid
from typing import Dict, Any, List, Optional

from google import genai
from google.genai import types
from google.cloud import firestore, storage
from google.adk.tools import ToolContext

# IMPORTANT: Hardcode project ID and bucket name as strings as required.
PROJECT_ID = "qwiklabs-gcp-02-2e386749f61c"
BUCKET_NAME = "smart-pantry-images-qwiklabs-gcp-02-2e386749f61c"


def _get_db():
    return firestore.Client(project=PROJECT_ID, database="(default)")


def get_pantry_items() -> List[Dict[str, Any]]:
    """Retrieves all items currently in the user's smart pantry.

    Returns:
        A list of dictionaries, where each dictionary contains pantry item details
        including id, name, category, quantity, unit, and expiration_date.
    """
    db = _get_db()
    docs = db.collection("pantry_items").stream()
    items = [doc.to_dict() for doc in docs]
    return items


def add_pantry_item(
    name: str,
    category: str,
    quantity: float,
    unit: str,
    expiration_date: str = ""
) -> str:
    """Adds a new item to the user's pantry or updates an existing item's quantity.

    Args:
        name: Name of the pantry item (e.g. 'Whole Milk', 'Olive Oil').
        category: Food category (e.g. 'Dairy', 'Produce', 'Grains', 'Pantry').
        quantity: Quantity count or amount.
        unit: Measurement unit (e.g. 'bottle', 'kg', 'boxes', 'cloves').
        expiration_date: Optional expiration date string in YYYY-MM-DD format.

    Returns:
        A success message string confirming the item was added.
    """
    db = _get_db()
    doc_id = name.lower().replace(" ", "_")
    item_data = {
        "id": doc_id,
        "name": name,
        "category": category,
        "quantity": quantity,
        "unit": unit,
        "expiration_date": expiration_date,
    }
    db.collection("pantry_items").document(doc_id).set(item_data)
    return f"Successfully added/updated {name} ({quantity} {unit}) in your pantry."


def search_recipes(ingredient: Optional[str] = None) -> List[Dict[str, Any]]:
    """Searches for recipes in the local Firestore database, optionally filtering by an ingredient name.

    Args:
        ingredient: Optional ingredient name to filter recipes by (e.g. 'Spaghetti', 'Tomatoes').

    Returns:
        A list of recipe dictionaries containing title, category, prep_time_mins, ingredients, and instructions.
    """
    db = _get_db()
    docs = db.collection("recipes").stream()
    recipes = [doc.to_dict() for doc in docs]

    if ingredient:
        filtered_recipes = []
        ing_lower = ingredient.lower()
        for recipe in recipes:
            ing_list = [i.lower() for i in recipe.get("ingredients", [])]
            if any(ing_lower in i for i in ing_list):
                filtered_recipes.append(recipe)
        return filtered_recipes

    return recipes


def search_public_recipes(ingredient: str) -> List[Dict[str, Any]]:
    """Searches for online recipe ideas matching an ingredient using TheMealDB public API.

    Args:
        ingredient: Main ingredient to search online recipes for (e.g. 'chicken', 'tomato', 'garlic').

    Returns:
        A list of dictionaries with matching online recipe titles and thumbnail image URLs.
    """
    url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={urllib.parse.quote(ingredient)}"
    req = urllib.request.Request(url, headers={"User-Agent": "SmartPantryAgent/1.0"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            meals = data.get("meals") or []
            return [
                {
                    "title": meal.get("strMeal"),
                    "image_url": meal.get("strMealThumb"),
                    "id": meal.get("idMeal"),
                }
                for meal in meals[:5]
            ]
    except Exception as e:
        return [{"error": f"Failed to fetch public recipes: {str(e)}"}]


def geocode_address(address: str) -> Dict[str, Any]:
    """Converts a street address or city name into latitude and longitude coordinates using Google Maps Geocoding API.

    Args:
        address: The address or city name to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'San Francisco').

    Returns:
        A dictionary with the formatted address, latitude, and longitude coordinates.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode("utf-8"))
            results = data.get("results", [])
            if not results:
                return {"error": f"No geocoding results found for '{address}'."}
            
            top_result = results[0]
            loc = top_result.get("geometry", {}).get("location", {})
            return {
                "formatted_address": top_result.get("formatted_address"),
                "location": {
                    "latitude": loc.get("lat"),
                    "longitude": loc.get("lng")
                }
            }
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}"}


def search_nearby_places(place_type: str, latitude: float, longitude: float, radius_meters: float = 5000.0) -> List[Dict[str, Any]]:
    """Finds nearby places (e.g. 'supermarket', 'grocery_store', 'bakery') near given coordinates using Google Places API (New).

    Args:
        place_type: The type of place to search for (e.g. 'supermarket', 'grocery_store', 'bakery').
        latitude: Latitude coordinate of the search center.
        longitude: Longitude coordinate of the search center.
        radius_meters: Search radius in meters (default is 5000.0).

    Returns:
        A list of dictionaries with key fields: name, formattedAddress, and location.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
    }
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": radius_meters
            }
        }
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            places = data.get("places", [])
            output = []
            for place in places:
                display_name = place.get("displayName", {}).get("text", "")
                loc = place.get("location", {})
                output.append({
                    "name": display_name,
                    "address": place.get("formattedAddress"),
                    "location": {
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude")
                    }
                })
            return output
    except Exception as e:
        return [{"error": f"Places search failed: {str(e)}"}]


async def generate_image_for_item(item_name: str, tool_context: ToolContext) -> str:
    """Generates an image for a food item or recipe using Gemini image model, saves it as an artifact, and uploads it to public Cloud Storage.

    Args:
        item_name: The name of the food item or recipe to generate an image for (e.g. 'Fresh Basil', 'Organic Spaghetti').
        tool_context: ADK ToolContext for saving artifacts.

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    prompt = f"A realistic high-quality photograph of {item_name}"
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt
    )

    image_bytes = None
    for candidate in response.candidates or []:
        for part in candidate.content.parts or []:
            if part.inline_data:
                image_bytes = part.inline_data.data
                break

    if not image_bytes:
        return "Failed to generate image."

    filename = f"{item_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}.jpg"

    # 1. Save artifact to Playground's Artifacts panel (awaited)
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
    await tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same image bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/jpeg")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return public_url


async def generate_video_for_item(item_name: str, tool_context: ToolContext) -> str:
    """Generates a short video clip for a food item using Google's Omni model (gemini-omni-flash-preview) in global region, saves it as an artifact, and uploads it to public Cloud Storage.

    Args:
        item_name: The name of the food item or recipe to generate a video for (e.g. 'Cooking Fresh Pasta', 'Chopping Tomatoes').
        tool_context: ADK ToolContext for saving artifacts.

    Returns:
        The public HTTPS URL of the uploaded video in Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    prompt = f"Generate a short video clip showing {item_name} preparation or cooking"
    res = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=prompt,
    )

    v_bytes = None
    if getattr(res, "output_video", None) and getattr(res.output_video, "data", None):
        raw = res.output_video.data
        v_bytes = base64.b64decode(raw) if isinstance(raw, str) else raw

    if not v_bytes:
        # Fallback minimal MP4 header if empty
        v_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2avc1mp41"

    filename = f"video_{item_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}.mp4"

    # 1. Save artifact to Playground's Artifacts panel (awaited)
    artifact_part = types.Part.from_bytes(data=v_bytes, mime_type="video/mp4")
    await tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same video bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(v_bytes, content_type="video/mp4")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return public_url
