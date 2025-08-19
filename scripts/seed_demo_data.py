#!/usr/bin/env python3
"""
Demo Data Seeding Script for Expense Tracker

This script generates realistic, anonymized demo data for presentations and testing.
It creates:
- Demo users with realistic profiles
- Diverse expense records with realistic patterns
- Budget configurations across different categories
- Realistic date distributions and amounts

The script is designed to be safe and reversible, with options to:
- Generate specific amounts of data
- Use consistent seeds for reproducible data
- Clear existing demo data before seeding
- Preserve real user data while adding demo data
"""

import os
import sys
import random
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

from faker import Faker
from dotenv import load_dotenv

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, engine
from app.models.user import User
from app.models.expense import Expense
from app.models.budget import Budget
import bcrypt

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


class DemoDataSeeder:
    """Generate realistic demo data for the Expense Tracker application."""
    
    def __init__(self, seed: Optional[int] = None):
        load_dotenv()
        
        # Initialize Faker with seed for reproducible data
        self.fake = Faker()
        if seed:
            Faker.seed(seed)
            random.seed(seed)
        
        # Demo data configuration
        self.demo_prefix = "demo_"
        self.demo_domain = "demo.example.com"
        
        # Expense categories with realistic spending patterns
        self.expense_categories = {
            "Food & Dining": {
                "subcategories": ["Restaurants", "Groceries", "Coffee Shops", "Fast Food", "Delivery"],
                "avg_amount": 25.0,
                "frequency": 0.8,  # High frequency
                "amount_variance": 0.6
            },
            "Transportation": {
                "subcategories": ["Gas", "Public Transit", "Uber/Taxi", "Parking", "Car Maintenance"],
                "avg_amount": 45.0,
                "frequency": 0.6,
                "amount_variance": 0.8
            },
            "Shopping": {
                "subcategories": ["Clothing", "Electronics", "Home & Garden", "Books", "Gifts"],
                "avg_amount": 75.0,
                "frequency": 0.4,
                "amount_variance": 1.2
            },
            "Entertainment": {
                "subcategories": ["Movies", "Concerts", "Games", "Sports", "Streaming"],
                "avg_amount": 35.0,
                "frequency": 0.5,
                "amount_variance": 0.9
            },
            "Bills & Utilities": {
                "subcategories": ["Electricity", "Internet", "Phone", "Insurance", "Subscriptions"],
                "avg_amount": 120.0,
                "frequency": 0.3,  # Monthly bills
                "amount_variance": 0.3
            },
            "Health & Medical": {
                "subcategories": ["Doctor Visits", "Pharmacy", "Gym", "Dental", "Insurance"],
                "avg_amount": 85.0,
                "frequency": 0.2,
                "amount_variance": 1.0
            },
            "Travel": {
                "subcategories": ["Hotels", "Flights", "Car Rental", "Activities", "Meals"],
                "avg_amount": 200.0,
                "frequency": 0.1,
                "amount_variance": 1.5
            },
            "Education": {
                "subcategories": ["Courses", "Books", "Supplies", "Tuition", "Workshops"],
                "avg_amount": 150.0,
                "frequency": 0.15,
                "amount_variance": 1.1
            }
        }
        
        # Realistic spending patterns by day of week (0=Monday)
        self.day_spending_multiplier = {
            0: 0.9,   # Monday - lower spending
            1: 0.95,  # Tuesday
            2: 1.0,   # Wednesday - average
            3: 1.05,  # Thursday
            4: 1.2,   # Friday - higher spending
            5: 1.3,   # Saturday - highest spending
            6: 1.1    # Sunday - moderate spending
        }
        
        # Currency options with weights
        self.currencies = [
            ("USD", 0.6),
            ("EUR", 0.2),
            ("GBP", 0.1),
            ("CAD", 0.05),
            ("AUD", 0.05)
        ]
    
    def create_demo_users(self, count: int = 5) -> List[User]:
        """Create demo users with realistic profiles."""
        print(f"🧑‍💼 Creating {count} demo users...")
        
        users = []
        db = SessionLocal()
        
        try:
            for i in range(count):
                # Generate realistic profile
                first_name = self.fake.first_name()
                last_name = self.fake.last_name()
                
                user = User(
                    username=f"{self.demo_prefix}{first_name.lower()}_{last_name.lower()}_{i+1}",
                    email=f"{first_name.lower()}.{last_name.lower()}@{self.demo_domain}",
                    hashed_password=get_password_hash("demo123"),  # Standard demo password
                    base_currency="USD"
                )
                
                db.add(user)
                users.append(user)
            
            db.commit()
            
            # Refresh to get IDs
            for user in users:
                db.refresh(user)
            
            print(f"✅ Created {len(users)} demo users")
            return users
            
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to create demo users: {e}")
            raise
        finally:
            db.close()
    
    def create_demo_expenses(self, users: List[User], days_back: int = 90, expenses_per_day: float = 2.5) -> List[Expense]:
        """Create realistic expense patterns for demo users."""
        print(f"💰 Creating demo expenses for the last {days_back} days...")
        
        expenses = []
        db = SessionLocal()
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            for user in users:
                # Generate user-specific spending profile
                user_spending_multiplier = random.uniform(0.7, 1.4)  # Some users spend more than others
                user_categories = random.sample(
                    list(self.expense_categories.keys()), 
                    k=random.randint(4, len(self.expense_categories))
                )
                
                # Generate expenses for each day
                current_date = start_date
                while current_date <= end_date:
                    # Determine number of expenses for this day
                    day_multiplier = self.day_spending_multiplier[current_date.weekday()]
                    # Use random.randint instead of poisson for simplicity
                    avg_daily = expenses_per_day * day_multiplier
                    daily_expenses = max(0, int(random.normalvariate(avg_daily, avg_daily * 0.3)))
                    
                    for _ in range(daily_expenses):
                        expense = self._generate_realistic_expense(
                            user, current_date, user_categories, user_spending_multiplier
                        )
                        if expense:
                            db.add(expense)
                            expenses.append(expense)
                    
                    current_date += timedelta(days=1)
            
            db.commit()
            print(f"✅ Created {len(expenses)} demo expenses")
            return expenses
            
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to create demo expenses: {e}")
            raise
        finally:
            db.close()
    
    def create_demo_budgets(self, users: List[User]) -> List[Budget]:
        """Create realistic budget configurations for demo users."""
        print(f"📊 Creating demo budgets...")
        
        budgets = []
        db = SessionLocal()
        
        try:
            for user in users:
                # Each user gets budgets for 3-6 random categories
                user_categories = random.sample(
                    list(self.expense_categories.keys()),
                    k=random.randint(3, 6)
                )
                
                for category in user_categories:
                    category_config = self.expense_categories[category]
                    
                    # Calculate realistic budget based on expected spending
                    base_monthly_budget = category_config["avg_amount"] * 30 * category_config["frequency"]
                    
                    # Add some variance (budgets are usually 10-50% above expected spending)
                    budget_multiplier = random.uniform(1.1, 1.5)
                    monthly_budget = base_monthly_budget * budget_multiplier
                    
                    # Create budget for current month
                    start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    
                    budget = Budget(
                        user_id=user.username,  # Budget model uses username as foreign key
                        category=category,
                        limit=float(monthly_budget)  # Budget model uses Float, not Decimal
                    )
                    
                    db.add(budget)
                    budgets.append(budget)
            
            db.commit()
            print(f"✅ Created {len(budgets)} demo budgets")
            return budgets
            
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to create demo budgets: {e}")
            raise
        finally:
            db.close()
    
    def _generate_realistic_expense(self, user: User, date: datetime, categories: List[str], spending_multiplier: float) -> Optional[Expense]:
        """Generate a single realistic expense."""
        # Skip some days randomly (people don't spend every day)
        if random.random() < 0.2:
            return None
        
        # Select category based on frequency
        category = random.choices(
            categories,
            weights=[self.expense_categories[cat]["frequency"] for cat in categories]
        )[0]
        
        category_config = self.expense_categories[category]
        
        # Generate realistic amount
        base_amount = category_config["avg_amount"]
        variance = category_config["amount_variance"]
        
        # Apply various multipliers
        amount = base_amount * spending_multiplier
        amount *= random.gauss(1.0, variance)  # Normal distribution centered at 1
        amount = max(1.0, amount)  # Minimum $1
        
        # Round to realistic precision
        if amount < 10:
            amount = round(amount, 2)
        elif amount < 100:
            amount = round(amount / 5) * 5  # Round to nearest $5
        else:
            amount = round(amount / 10) * 10  # Round to nearest $10
        
        # Select subcategory and generate description
        subcategory = random.choice(category_config["subcategories"])
        description = self._generate_expense_description(category, subcategory)
        
        # Select currency (mostly USD for simplicity)
        currency = random.choices(
            [curr for curr, _ in self.currencies],
            weights=[weight for _, weight in self.currencies]
        )[0]
        
        # Add some time variation to the date
        expense_time = date + timedelta(
            hours=random.randint(6, 23),
            minutes=random.randint(0, 59)
        )
        
        return Expense(
            user_id=user.username,  # Expense model uses username as foreign key
            amount=float(amount),   # Expense model uses Float, not Decimal
            title=description,      # Expense model uses 'title' not 'description' 
            category=category,
            date=expense_time.date(),  # Expense model uses Date, not DateTime
            currency=currency
        )
    
    def _generate_expense_description(self, category: str, subcategory: str) -> str:
        """Generate realistic expense descriptions."""
        descriptions = {
            "Restaurants": [
                "Dinner at {}", "Lunch at {}", "Brunch at {}", "Date night at {}",
                "Team lunch at {}", "Birthday dinner at {}", "Quick bite at {}"
            ],
            "Groceries": [
                "Weekly grocery shopping", "Grocery run", "Fresh produce shopping",
                "Bulk shopping", "Organic groceries", "Specialty items", "Emergency grocery run"
            ],
            "Coffee Shops": [
                "Morning coffee", "Coffee meeting", "Afternoon coffee break",
                "Coffee and pastry", "Work coffee", "Weekend coffee", "Coffee date"
            ],
            "Gas": [
                "Gas station fill-up", "Fuel", "Gas for road trip", "Emergency gas",
                "Monthly gas fill-up", "Commute fuel", "Gas station stop"
            ],
            "Uber/Taxi": [
                "Uber to airport", "Taxi home", "Ride to meeting", "Late night ride",
                "Uber to work", "Ride sharing", "Emergency ride"
            ],
            "Movies": [
                "Movie tickets", "Cinema night", "Date movie", "IMAX experience",
                "Movie with friends", "Weekend movie", "New release movie"
            ],
            "Electronics": [
                "Phone accessories", "Laptop repair", "New headphones", "Cable purchase",
                "Tech gadget", "Software subscription", "Computer upgrade"
            ]
        }
        
        if subcategory in descriptions:
            template = random.choice(descriptions[subcategory])
            if "{}" in template:
                # Generate a business name
                business_name = self.fake.company()
                return template.format(business_name)
            return template
        
        # Fallback to generic description
        return f"{subcategory} - {self.fake.catch_phrase()}"
    
    def _get_month_end(self, start_date: datetime) -> datetime:
        """Get the last day of the month for a given start date."""
        if start_date.month == 12:
            next_month = start_date.replace(year=start_date.year + 1, month=1, day=1)
        else:
            next_month = start_date.replace(month=start_date.month + 1, day=1)
        
        return next_month - timedelta(days=1)
    
    def clear_demo_data(self):
        """Remove all demo data (users with demo_ prefix and their associated data)."""
        print("🧹 Clearing existing demo data...")
        
        db = SessionLocal()
        try:
            # Find demo users
            demo_users = db.query(User).filter(User.username.like(f"{self.demo_prefix}%")).all()
            
            if not demo_users:
                print("ℹ️  No demo data found to clear")
                return
            
            demo_user_ids = [user.id for user in demo_users]
            
            # Delete expenses
            expenses_deleted = db.query(Expense).filter(Expense.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
            print(f"   🗑️  Deleted {expenses_deleted} demo expenses")
            
            # Delete budgets
            budgets_deleted = db.query(Budget).filter(Budget.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
            print(f"   🗑️  Deleted {budgets_deleted} demo budgets")
            
            # Delete users
            users_deleted = db.query(User).filter(User.username.like(f"{self.demo_prefix}%")).delete(synchronize_session=False)
            print(f"   🗑️  Deleted {users_deleted} demo users")
            
            db.commit()
            print("✅ Demo data cleared successfully")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to clear demo data: {e}")
            raise
        finally:
            db.close()
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate a summary report of demo data."""
        db = SessionLocal()
        try:
            demo_users = db.query(User).filter(User.username.like(f"{self.demo_prefix}%")).all()
            demo_user_ids = [user.id for user in demo_users]
            
            if not demo_user_ids:
                return {"message": "No demo data found"}
            
            # Count expenses by category
            expenses = db.query(Expense).filter(Expense.user_id.in_(demo_user_ids)).all()
            category_spending = {}
            total_spending = Decimal('0')
            
            for expense in expenses:
                category_spending[expense.category] = category_spending.get(expense.category, Decimal('0')) + expense.amount
                total_spending += expense.amount
            
            # Count budgets
            budgets = db.query(Budget).filter(Budget.user_id.in_(demo_user_ids)).all()
            
            return {
                "users": len(demo_users),
                "expenses": len(expenses),
                "budgets": len(budgets),
                "total_spending": float(total_spending),
                "category_spending": {k: float(v) for k, v in category_spending.items()},
                "date_range": {
                    "earliest_expense": min([e.date for e in expenses]).isoformat() if expenses else None,
                    "latest_expense": max([e.date for e in expenses]).isoformat() if expenses else None
                }
            }
            
        finally:
            db.close()


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Demo data seeding utility for Expense Tracker")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible data")
    parser.add_argument("--users", type=int, default=5, help="Number of demo users to create")
    parser.add_argument("--days", type=int, default=90, help="Number of days of expense history")
    parser.add_argument("--expenses-per-day", type=float, default=2.5, help="Average expenses per user per day")
    parser.add_argument("--clear", action="store_true", help="Clear existing demo data before seeding")
    parser.add_argument("--clear-only", action="store_true", help="Only clear demo data (don't seed new)")
    parser.add_argument("--summary", action="store_true", help="Show summary of existing demo data")
    
    args = parser.parse_args()
    
    seeder = DemoDataSeeder(seed=args.seed)
    
    try:
        if args.summary:
            print("📊 Demo Data Summary")
            print("=" * 50)
            summary = seeder.generate_summary_report()
            print(json.dumps(summary, indent=2))
            return
        
        if args.clear or args.clear_only:
            seeder.clear_demo_data()
        
        if not args.clear_only:
            print(f"🌱 Seeding demo data...")
            print(f"   👥 Users: {args.users}")
            print(f"   📅 Days of history: {args.days}")
            print(f"   💰 Avg expenses/day: {args.expenses_per_day}")
            if args.seed:
                print(f"   🎲 Seed: {args.seed}")
            print()
            
            # Create demo data
            users = seeder.create_demo_users(args.users)
            expenses = seeder.create_demo_expenses(users, args.days, args.expenses_per_day)
            budgets = seeder.create_demo_budgets(users)
            
            print()
            print("🎉 Demo data seeding complete!")
            print("=" * 50)
            print(f"✅ Created {len(users)} demo users")
            print(f"✅ Created {len(expenses)} demo expenses")
            print(f"✅ Created {len(budgets)} demo budgets")
            print()
            print("🔑 Demo Login Credentials:")
            print("   Username: demo_[firstname]_[lastname]_[number]")
            print("   Password: demo123")
            print(f"   Email domain: {seeder.demo_domain}")
            print()
            print("💡 Use --summary to see detailed statistics")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
