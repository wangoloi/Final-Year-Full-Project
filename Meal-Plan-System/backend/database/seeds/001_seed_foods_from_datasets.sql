-- Seed Foods from diabetic_diet_meal_plans_with_macros_GI.csv
-- Run after 001_initial_schema.sql
-- Extracts unique dishes and inserts as food items

-- Sample seed data (unique dishes from dataset - first occurrence used for macros)
INSERT INTO food (id, name, category, calories, protein, carbs, fat, fiber, glycemic_index, description, tags) VALUES
(uuid_generate_v4(), 'Oats porridge with flax seeds + 2 boiled eggs', 'breakfast', 336.0, 19.2, 33.6, 11.5, 5.8, 55, 'High-fiber breakfast with protein', '["diabetic_friendly", "high_protein", "low_gi"]'),
(uuid_generate_v4(), 'Whole wheat chapati + palak paneer + cucumber salad', 'lunch', 403.2, 17.3, 43.2, 11.5, 7.7, 50, 'Indian diabetic-friendly lunch', '["diabetic_friendly", "vegetarian", "fiber_rich"]'),
(uuid_generate_v4(), 'Roasted chana + Greek yogurt (unsweetened)', 'snack', 240.0, 14.4, 19.2, 7.7, 5.8, 35, 'Protein-rich low GI snack', '["diabetic_friendly", "high_protein", "low_gi"]'),
(uuid_generate_v4(), 'Grilled tofu + sautéed vegetables', 'dinner', 307.2, 21.1, 17.3, 11.5, 6.7, 40, 'Low-carb vegetarian dinner', '["diabetic_friendly", "vegetarian", "low_carb"]'),
(uuid_generate_v4(), 'Oats porridge + boiled egg whites + milk', 'breakfast', 345.6, 23.0, 28.8, 9.6, 4.8, 55, 'High-protein breakfast', '["diabetic_friendly", "high_protein"]'),
(uuid_generate_v4(), 'Brown rice + grilled chicken curry + salad', 'lunch', 460.8, 30.7, 48.0, 13.4, 5.8, 58, 'Balanced non-veg lunch', '["diabetic_friendly", "high_protein"]'),
(uuid_generate_v4(), 'Boiled egg + roasted peanuts', 'snack', 259.2, 17.3, 9.6, 14.4, 3.8, 35, 'High-protein low-carb snack', '["diabetic_friendly", "high_protein", "low_gi"]'),
(uuid_generate_v4(), 'Grilled fish + sautéed vegetables', 'dinner', 336.0, 28.8, 14.4, 13.4, 5.8, 42, 'Omega-3 rich dinner', '["diabetic_friendly", "high_protein", "low_carb"]')
ON CONFLICT DO NOTHING;
