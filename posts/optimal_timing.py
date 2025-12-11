"""
Optimal Posting Time Analysis Service
Analyzes best times to post on different social media platforms based on industry research and user engagement patterns
"""

import logging
from datetime import datetime, time, timedelta
from django.utils import timezone
from typing import Dict, List, Optional, Tuple
from accounts.models import CompanyProfile

logger = logging.getLogger(__name__)


class OptimalTimingService:
    """Service for analyzing optimal posting times for social media platforms"""
    
    # Industry-based optimal posting times (in hours, 0-23)
    # Based on research: engagement patterns vary by platform and industry
    PLATFORM_OPTIMAL_HOURS = {
        'facebook': {
            'default': [9, 13, 15, 17, 19],  # 9AM, 1PM, 3PM, 5PM, 7PM
            'technology': [8, 12, 14, 16, 18],
            'healthcare': [7, 12, 15, 18],
            'finance': [8, 11, 14, 17],
            'education': [7, 12, 15, 19],
            'retail': [10, 13, 16, 19, 21],
            'food_beverage': [11, 14, 18, 20],
            'travel_tourism': [9, 13, 17, 20],
            'fashion': [10, 14, 18, 21],
            'sports_fitness': [6, 12, 17, 20],
            'entertainment': [12, 16, 19, 21],
        },
        'instagram': {
            'default': [11, 13, 15, 17, 19, 21],  # 11AM, 1PM, 3PM, 5PM, 7PM, 9PM
            'technology': [9, 12, 15, 18, 20],
            'healthcare': [7, 12, 17, 19],
            'finance': [8, 12, 16, 18],
            'education': [8, 13, 16, 19],
            'retail': [10, 13, 16, 19, 21],
            'food_beverage': [11, 14, 18, 20, 22],
            'travel_tourism': [9, 13, 17, 20],
            'fashion': [10, 13, 17, 20, 22],
            'sports_fitness': [6, 12, 17, 20],
            'entertainment': [12, 16, 19, 21, 23],
        },
        'linkedin': {
            'default': [8, 12, 17],  # 8AM, 12PM, 5PM (business hours)
            'technology': [7, 11, 14, 17],
            'healthcare': [7, 12, 16],
            'finance': [7, 11, 15, 17],
            'education': [8, 12, 16],
            'retail': [9, 13, 17],
            'food_beverage': [10, 13, 17],
            'travel_tourism': [9, 13, 17],
            'fashion': [9, 13, 17],
            'sports_fitness': [7, 12, 17],
            'entertainment': [10, 14, 17],
        },
        'youtube': {
            'default': [14, 16, 18, 20],  # 2PM, 4PM, 6PM, 8PM
            'technology': [13, 16, 19, 21],
            'healthcare': [12, 15, 18],
            'finance': [12, 15, 18],
            'education': [13, 16, 19],
            'retail': [14, 17, 20],
            'food_beverage': [13, 17, 20],
            'travel_tourism': [14, 18, 21],
            'fashion': [14, 17, 20, 22],
            'sports_fitness': [12, 17, 20],
            'entertainment': [15, 18, 21],
        },
        'tiktok': {
            'default': [9, 12, 15, 18, 21],  # 9AM, 12PM, 3PM, 6PM, 9PM
            'technology': [10, 13, 17, 20],
            'healthcare': [8, 12, 17, 20],
            'finance': [9, 13, 17],
            'education': [9, 13, 17, 20],
            'retail': [10, 14, 18, 21],
            'food_beverage': [11, 14, 18, 21],
            'travel_tourism': [10, 14, 18, 21],
            'fashion': [11, 15, 19, 22],
            'sports_fitness': [7, 12, 17, 20],
            'entertainment': [12, 16, 19, 22],
        },
        'twitter': {
            'default': [8, 12, 15, 17, 20],  # 8AM, 12PM, 3PM, 5PM, 8PM
            'technology': [7, 11, 14, 17, 20],
            'healthcare': [7, 12, 16, 19],
            'finance': [7, 11, 15, 17],
            'education': [8, 12, 16, 19],
            'retail': [9, 13, 16, 19],
            'food_beverage': [10, 13, 17, 20],
            'travel_tourism': [9, 13, 17, 20],
            'fashion': [10, 14, 18, 21],
            'sports_fitness': [7, 12, 17, 20],
            'entertainment': [12, 16, 19, 21],
        },
    }
    
    # Best days of week for each platform (0=Monday, 6=Sunday)
    PLATFORM_OPTIMAL_DAYS = {
        'facebook': [1, 2, 3, 4, 5],  # Tuesday-Saturday
        'instagram': [1, 2, 3, 4, 5, 6],  # Tuesday-Sunday
        'linkedin': [1, 2, 3, 4],  # Tuesday-Friday (business days)
        'youtube': [0, 1, 2, 3, 4, 5, 6],  # All days
        'tiktok': [1, 2, 3, 4, 5, 6],  # Tuesday-Sunday
        'twitter': [1, 2, 3, 4, 5],  # Tuesday-Saturday
    }
    
    def __init__(self, user=None):
        """Initialize with user context"""
        self.user = user
        self.company_profile = None
        if user:
            try:
                self.company_profile = CompanyProfile.objects.get(user=user)
            except CompanyProfile.DoesNotExist:
                pass
    
    def get_optimal_hours(self, platform: str) -> List[int]:
        """
        Get optimal posting hours for a platform based on user's industry
        
        Args:
            platform: Platform name (facebook, instagram, linkedin, youtube, tiktok, twitter)
        
        Returns:
            List of optimal hours (0-23)
        """
        platform = platform.lower()
        
        if platform not in self.PLATFORM_OPTIMAL_HOURS:
            logger.warning(f"Platform {platform} not found in optimal hours, using default")
            return [9, 13, 17]  # Default: 9AM, 1PM, 5PM
        
        industry_hours = self.PLATFORM_OPTIMAL_HOURS[platform]
        
        # Get industry from company profile
        industry = 'default'
        if self.company_profile and self.company_profile.industry:
            industry = self.company_profile.industry
            if industry not in industry_hours:
                industry = 'default'
        
        return industry_hours.get(industry, industry_hours['default'])
    
    def get_optimal_days(self, platform: str) -> List[int]:
        """
        Get optimal posting days for a platform
        
        Args:
            platform: Platform name
        
        Returns:
            List of optimal day numbers (0=Monday, 6=Sunday)
        """
        platform = platform.lower()
        return self.PLATFORM_OPTIMAL_DAYS.get(platform, [1, 2, 3, 4, 5])  # Default: Tuesday-Saturday
    
    def suggest_optimal_time(
        self, 
        platform: str, 
        start_date: Optional[datetime] = None,
        days_ahead: int = 7
    ) -> List[Dict]:
        """
        Suggest optimal posting times for a platform
        
        Args:
            platform: Platform name
            start_date: Start date for suggestions (default: now)
            days_ahead: Number of days to suggest ahead
        
        Returns:
            List of suggested datetime objects with scores
        """
        if start_date is None:
            start_date = timezone.now()
        
        optimal_hours = self.get_optimal_hours(platform)
        optimal_days = self.get_optimal_days(platform)
        
        suggestions = []
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day_offset in range(days_ahead):
            check_date = current_date + timedelta(days=day_offset)
            day_of_week = check_date.weekday()  # 0=Monday, 6=Sunday
            
            # Check if this day is optimal
            if day_of_week not in optimal_days:
                continue
            
            # Generate suggestions for each optimal hour
            for hour in optimal_hours:
                suggested_time = check_date.replace(hour=hour, minute=0)
                
                # Skip if time is in the past
                if suggested_time <= timezone.now():
                    continue
                
                # Calculate score based on day and hour
                score = self._calculate_time_score(platform, day_of_week, hour)
                
                suggestions.append({
                    'datetime': suggested_time,
                    'date': suggested_time.date(),
                    'time': suggested_time.time(),
                    'hour': hour,
                    'day_of_week': day_of_week,
                    'day_name': check_date.strftime('%A'),
                    'score': score,
                    'platform': platform
                })
        
        # Sort by score (highest first) and datetime
        suggestions.sort(key=lambda x: (-x['score'], x['datetime']))
        
        return suggestions[:10]  # Return top 10 suggestions
    
    def _calculate_time_score(self, platform: str, day_of_week: int, hour: int) -> float:
        """
        Calculate a score for a specific time slot
        
        Args:
            platform: Platform name
            day_of_week: Day of week (0=Monday, 6=Sunday)
            hour: Hour of day (0-23)
        
        Returns:
            Score (0.0-1.0, higher is better)
        """
        score = 0.5  # Base score
        
        # Day score
        optimal_days = self.get_optimal_days(platform)
        if day_of_week in optimal_days:
            # Higher score for mid-week (Tuesday-Thursday)
            if day_of_week in [1, 2, 3]:
                score += 0.3
            else:
                score += 0.2
        
        # Hour score
        optimal_hours = self.get_optimal_hours(platform)
        if hour in optimal_hours:
            # Peak hours (lunch and evening) get higher scores
            if hour in [12, 13, 17, 18, 19, 20]:
                score += 0.3
            else:
                score += 0.2
        
        # Avoid very early or very late hours
        if hour < 6 or hour > 23:
            score -= 0.2
        
        return min(1.0, max(0.0, score))
    
    def get_best_time_for_platforms(
        self, 
        platforms: List[str],
        start_date: Optional[datetime] = None,
        days_ahead: int = 7
    ) -> Dict[str, List[Dict]]:
        """
        Get optimal times for multiple platforms
        
        Args:
            platforms: List of platform names
            start_date: Start date for suggestions
            days_ahead: Number of days to suggest ahead
        
        Returns:
            Dictionary mapping platform to list of suggestions
        """
        result = {}
        
        for platform in platforms:
            suggestions = self.suggest_optimal_time(platform, start_date, days_ahead)
            result[platform] = suggestions
        
        return result
    
    def find_common_optimal_time(
        self,
        platforms: List[str],
        start_date: Optional[datetime] = None,
        days_ahead: int = 7
    ) -> List[Dict]:
        """
        Find times that are optimal for multiple platforms simultaneously
        
        Args:
            platforms: List of platform names
            start_date: Start date for suggestions
            days_ahead: Number of days to suggest ahead
        
        Returns:
            List of suggested times with platform scores
        """
        if not platforms:
            return []
        
        # Get suggestions for all platforms
        all_suggestions = {}
        for platform in platforms:
            all_suggestions[platform] = self.suggest_optimal_time(platform, start_date, days_ahead)
        
        # Find common times (within 1 hour window)
        common_times = []
        time_windows = {}
        
        for platform, suggestions in all_suggestions.items():
            for suggestion in suggestions:
                dt = suggestion['datetime']
                # Round to nearest hour for grouping
                window_key = dt.replace(minute=0, second=0, microsecond=0)
                
                if window_key not in time_windows:
                    time_windows[window_key] = {
                        'datetime': window_key,
                        'platforms': {},
                        'total_score': 0.0
                    }
                
                time_windows[window_key]['platforms'][platform] = suggestion['score']
                time_windows[window_key]['total_score'] += suggestion['score']
        
        # Convert to list and sort by total score
        for window_key, window_data in time_windows.items():
            # Only include if optimal for at least 2 platforms or high score
            if len(window_data['platforms']) >= 2 or window_data['total_score'] >= 0.8:
                common_times.append({
                    'datetime': window_data['datetime'],
                    'date': window_data['datetime'].date(),
                    'time': window_data['datetime'].time(),
                    'platforms': window_data['platforms'],
                    'total_score': window_data['total_score'],
                    'platform_count': len(window_data['platforms'])
                })
        
        # Sort by total score and platform count
        common_times.sort(key=lambda x: (-x['total_score'], -x['platform_count'], x['datetime']))
        
        return common_times[:15]  # Return top 15 common times

