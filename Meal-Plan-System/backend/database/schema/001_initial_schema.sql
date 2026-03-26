-- Smart Diabetes Nutrition & Monitoring Platform
-- Initial PostgreSQL Schema
-- Naming: snake_case, singular table names

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- CORE TABLES
-- =============================================================================

CREATE TABLE "user" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'patient' CHECK (role IN ('patient', 'dietitian', 'admin')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_email ON "user"(email);
CREATE INDEX idx_user_role ON "user"(role);

-- -----------------------------------------------------------------------------
CREATE TABLE user_profile (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,
    height DECIMAL(5,2),  -- cm
    weight DECIMAL(5,2),  -- kg
    bmi DECIMAL(4,2),
    diabetes_type VARCHAR(50) CHECK (diabetes_type IN ('type_1', 'type_2', 'gestational', 'prediabetes', NULL)),
    diagnosis_date DATE,
    activity_level VARCHAR(50) CHECK (activity_level IN ('sedentary', 'light', 'moderate', 'active', 'very_active')),
    dietary_restrictions JSONB DEFAULT '[]',
    allergies JSONB DEFAULT '[]',
    target_glucose_min DECIMAL(5,2),
    target_glucose_max DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_user_profile_user_id ON user_profile(user_id);

-- -----------------------------------------------------------------------------
CREATE TABLE food (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    calories DECIMAL(8,2) NOT NULL CHECK (calories >= 0),
    protein DECIMAL(8,2) NOT NULL DEFAULT 0 CHECK (protein >= 0),
    carbs DECIMAL(8,2) NOT NULL DEFAULT 0 CHECK (carbs >= 0),
    fat DECIMAL(8,2) NOT NULL DEFAULT 0 CHECK (fat >= 0),
    fiber DECIMAL(8,2) DEFAULT 0 CHECK (fiber >= 0),
    glycemic_index INTEGER CHECK (glycemic_index BETWEEN 0 AND 100),
    description TEXT,
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_food_category ON food(category);
CREATE INDEX idx_food_glycemic_index ON food(glycemic_index);
CREATE INDEX idx_food_tags ON food USING GIN(tags);
-- Optional: CREATE EXTENSION pg_trgm; then: CREATE INDEX idx_food_name_trgm ON food USING GIN(name gin_trgm_ops);

-- -----------------------------------------------------------------------------
CREATE TABLE meal (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    meal_type VARCHAR(50) NOT NULL CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'other')),
    meal_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    total_calories DECIMAL(8,2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_meal_user_time ON meal(user_id, meal_time DESC);
CREATE INDEX idx_meal_user_id ON meal(user_id);

-- -----------------------------------------------------------------------------
CREATE TABLE meal_item (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meal_id UUID NOT NULL REFERENCES meal(id) ON DELETE CASCADE,
    food_id UUID NOT NULL REFERENCES food(id) ON DELETE RESTRICT,
    quantity DECIMAL(8,2) NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit VARCHAR(50) NOT NULL DEFAULT 'serving',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_meal_item_meal_id ON meal_item(meal_id);
CREATE INDEX idx_meal_item_food_id ON meal_item(food_id);

-- -----------------------------------------------------------------------------
CREATE TABLE glucose_reading (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    reading_value DECIMAL(6,2) NOT NULL CHECK (reading_value >= 0 AND reading_value <= 600),
    reading_type VARCHAR(50) NOT NULL CHECK (reading_type IN ('fasting', 'pre_meal', 'post_meal', 'random', 'bedtime', 'hba1c')),
    reading_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    meal_context TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_glucose_user_time ON glucose_reading(user_id, reading_time DESC);
CREATE INDEX idx_glucose_reading_time ON glucose_reading(reading_time);
CREATE INDEX idx_glucose_user_recent ON glucose_reading(user_id, reading_time DESC) 
    WHERE reading_time >= NOW() - INTERVAL '90 days';

-- -----------------------------------------------------------------------------
CREATE TABLE goal (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    goal_type VARCHAR(50) NOT NULL CHECK (goal_type IN ('weight', 'glucose', 'hba1c', 'time_in_range', 'nutrition', 'activity')),
    target_value DECIMAL(12,4) NOT NULL,
    current_value DECIMAL(12,4),
    unit VARCHAR(50),
    deadline DATE,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_goal_user_type ON goal(user_id, goal_type);
CREATE INDEX idx_goal_active ON goal(user_id, deadline) WHERE status = 'active' AND deadline >= CURRENT_DATE;

-- -----------------------------------------------------------------------------
CREATE TABLE dietitian (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,
    license_number VARCHAR(100),
    specialization VARCHAR(255),
    verified_status VARCHAR(50) DEFAULT 'pending' CHECK (verified_status IN ('pending', 'verified', 'rejected')),
    bio TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_dietitian_user_id ON dietitian(user_id);

-- -----------------------------------------------------------------------------
CREATE TABLE message (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    receiver_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    read_status BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_message_sender_receiver ON message(sender_id, receiver_id, created_at DESC);
CREATE INDEX idx_message_receiver_unread ON message(receiver_id, read_status) WHERE read_status = FALSE;

-- =============================================================================
-- CONVERSATION STORAGE (for Chatbot RAG)
-- =============================================================================

CREATE TABLE conversation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    title VARCHAR(255) DEFAULT 'New Conversation',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE conversation_message (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_conversation_user ON conversation(user_id);
CREATE INDEX idx_conversation_message_conv ON conversation_message(conversation_id);

-- =============================================================================
-- UPDATED_AT TRIGGER
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_updated_at BEFORE UPDATE ON "user"
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_user_profile_updated_at BEFORE UPDATE ON user_profile
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_food_updated_at BEFORE UPDATE ON food
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_meal_updated_at BEFORE UPDATE ON meal
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_goal_updated_at BEFORE UPDATE ON goal
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_dietitian_updated_at BEFORE UPDATE ON dietitian
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
