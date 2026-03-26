-- Rollback for 001_initial_schema.sql
-- Run in reverse order of creation

DROP TRIGGER IF EXISTS update_dietitian_updated_at ON dietitian;
DROP TRIGGER IF EXISTS update_goal_updated_at ON goal;
DROP TRIGGER IF EXISTS update_meal_updated_at ON meal;
DROP TRIGGER IF EXISTS update_food_updated_at ON food;
DROP TRIGGER IF EXISTS update_user_profile_updated_at ON user_profile;
DROP TRIGGER IF EXISTS update_user_updated_at ON "user";

DROP FUNCTION IF EXISTS update_updated_at_column();

DROP TABLE IF EXISTS conversation_message;
DROP TABLE IF EXISTS conversation;
DROP TABLE IF EXISTS message;
DROP TABLE IF EXISTS dietitian;
DROP TABLE IF EXISTS goal;
DROP TABLE IF EXISTS glucose_reading;
DROP TABLE IF EXISTS meal_item;
DROP TABLE IF EXISTS meal;
DROP TABLE IF EXISTS food;
DROP TABLE IF EXISTS user_profile;
DROP TABLE IF EXISTS "user";
