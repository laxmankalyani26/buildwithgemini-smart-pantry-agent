"""
Seed Firestore database for smart-pantry-agent.
"""
import google.auth
from google.cloud import firestore

# IMPORTANT: Hardcode project ID as a string as required.
PROJECT_ID = "qwiklabs-gcp-02-2e386749f61c"

def seed_database():
    credentials, _ = google.auth.default()
    db = firestore.Client(project=PROJECT_ID, credentials=credentials, database="(default)")
    print(f"Connecting to Firestore for project: {PROJECT_ID}")

    # Seed pantry_items collection
    pantry_items = [
        {
            "id": "pantry_001",
            "name": "Extra Virgin Olive Oil",
            "category": "Pantry",
            "quantity": 1,
            "unit": "bottle",
            "expiration_date": "2027-01-01",
        },
        {
            "id": "pantry_002",
            "name": "Organic Spaghetti",
            "category": "Grains",
            "quantity": 2,
            "unit": "boxes",
            "expiration_date": "2026-12-31",
        },
        {
            "id": "pantry_003",
            "name": "Fresh Garlic",
            "category": "Produce",
            "quantity": 6,
            "unit": "cloves",
            "expiration_date": "2026-10-10",
        },
        {
            "id": "pantry_004",
            "name": "Parmesan Cheese",
            "category": "Dairy",
            "quantity": 200,
            "unit": "grams",
            "expiration_date": "2026-10-20",
        },
        {
            "id": "pantry_005",
            "name": "Ripe Tomatoes",
            "category": "Produce",
            "quantity": 4,
            "unit": "items",
            "expiration_date": "2026-09-30",
        },
        {
            "id": "pantry_006",
            "name": "Fresh Basil",
            "category": "Produce",
            "quantity": 1,
            "unit": "bunch",
            "expiration_date": "2026-09-29",
        },
    ]

    pantry_ref = db.collection("pantry_items")
    for item in pantry_items:
        doc_id = item["id"]
        pantry_ref.document(doc_id).set(item)
        print(f"Seeded pantry item: {item['name']} ({doc_id})")

    # Seed recipes collection
    recipes = [
        {
            "id": "recipe_001",
            "title": "Classic Tomato Basil Spaghetti",
            "category": "Italian",
            "prep_time_mins": 20,
            "ingredients": ["Organic Spaghetti", "Ripe Tomatoes", "Fresh Garlic", "Extra Virgin Olive Oil", "Fresh Basil", "Parmesan Cheese"],
            "instructions": "1. Boil spaghetti in salted water. 2. Saute garlic and diced tomatoes in olive oil. 3. Toss spaghetti with tomato sauce and top with fresh basil and parmesan cheese.",
        },
        {
            "id": "recipe_002",
            "title": "Garlic & Olive Oil Pasta (Spaghetti Aglio e Olio)",
            "category": "Italian",
            "prep_time_mins": 15,
            "ingredients": ["Organic Spaghetti", "Fresh Garlic", "Extra Virgin Olive Oil", "Parmesan Cheese"],
            "instructions": "1. Cook pasta until al dente. 2. Gently brown sliced garlic in olive oil. 3. Toss pasta with garlic oil and parmesan cheese.",
        }
    ]

    recipes_ref = db.collection("recipes")
    for recipe in recipes:
        doc_id = recipe["id"]
        recipes_ref.document(doc_id).set(recipe)
        print(f"Seeded recipe: {recipe['title']} ({doc_id})")

    print("Firestore seeding complete!")

if __name__ == "__main__":
    seed_database()
