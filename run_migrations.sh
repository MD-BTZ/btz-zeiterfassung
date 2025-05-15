#!/bin/bash
# Script to run all migrations for the attendance application
# This ensures the database schema is properly updated

echo "Running database migration sequence..."

# Step 1: Run the base migration
echo "Step 1: Running base database migration..."
python migrate_db.py

# Step 2: Run fix_settings script
echo "Step 2: Running settings fix script..."
python fix_settings.py

# Step 3: Run ArbZG migration
echo "Step 3: Running ArbZG migration..."
python migrate_arbzg.py

# Step 4: Add ArbZG-compliant breaks to existing records
echo "Step 4: Adding ArbZG-compliant breaks to existing records..."
python add_arbzg_breaks.py

# Step 5: Enhance existing ArbZG breaks with intelligent placement
echo "Step 5: Enhancing existing breaks with intelligent placement..."
python add_arbzg_breaks_v2.py

# Step 6: Run the schema checker and fixer
echo "Step 6: Running database schema checker and fixer..."
python check_and_fix_db.py

echo "Migration sequence completed!"
echo "Your database now has proper support for ArbZG-compliant breaks with intelligent placement."
