"""
Instagram Metrics Computation Module

Pure functions that calculate metrics from profile data.
No AI, no guessing, just deterministic calculations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import Counter
import statistics


class InstagramMetrics:
    """Instagram profile metrics calculator"""
    
    @staticmethod
    def compute_engagement_rate(
        followers: int,
        posts: int,
        account_stage: str,
        posting_frequency: str
    ) -> float:
        """
        Calculate estimated engagement rate based on account metrics
        
        Formula based on industry benchmarks:
        - Starter accounts (0-1K): 5.0% base
        - Growing accounts (1K-10K): 4.0% base
        - Established accounts (10K-100K): 3.0% base
        - Influencer accounts (100K+): 2.5% base
        
        Adjusted by posting frequency (more posts = lower per-post engagement)
        """
        if posts == 0 or followers == 0:
            return 0.0
        
        # Base engagement rate by account stage (industry benchmarks)
        base_rates = {
            "starter": 5.0,
            "growing": 4.0,
            "established": 3.0,
            "influencer": 2.5
        }
        base_engagement = base_rates.get(account_stage, 3.5)
        
        # Frequency multiplier (less frequent = higher engagement per post)
        frequency_multipliers = {
            '1-2': 1.2,
            '3-4': 1.0,
            '5-7': 0.9,
            'daily': 0.8,
            '2plus': 0.7
        }
        frequency_multiplier = frequency_multipliers.get(posting_frequency, 1.0)
        
        return round(base_engagement * frequency_multiplier, 1)
    
    @staticmethod
    def compute_following_ratio(followers: int, following: int) -> float:
        """Calculate following/followers ratio"""
        if followers == 0:
            return 0.0
        return round(following / followers, 2)
    
    @staticmethod
    def compute_posts_per_follower(posts: int, followers: int) -> float:
        """Calculate content density (posts per follower)"""
        if followers == 0:
            return 0.0
        return round(posts / followers, 4)
    
    @staticmethod
    def determine_account_stage(followers: int) -> tuple[str, str]:
        """
        Determine account stage based on follower count
        Returns: (stage_en, stage_az)
        """
        if followers < 1000:
            return ("starter", "Başlanğıc")
        elif followers < 10000:
            return ("growing", "İnkişaf mərhələsi")
        elif followers < 100000:
            return ("established", "Möhkəm")
        else:
            return ("influencer", "İnfluenser")
    
    @staticmethod
    def normalize_posting_frequency(freq_code: str) -> str:
        """Map frequency code to readable format"""
        frequency_map = {
            '1-2': 'Həftədə 1-2 dəfə',
            '3-4': 'Həftədə 3-4 dəfə',
            '5-7': 'Həftədə 5-7 dəfə',
            'daily': 'Gündə 1 dəfə',
            '2plus': 'Gündə 2+ dəfə'
        }
        return frequency_map.get(freq_code, freq_code or 'Təyin olunmayıb')
    
    @staticmethod
    def compute_all_metrics(
        username: str,
        followers: int,
        following: int,
        posts: int,
        posting_frequency: str,
        niche: Optional[str] = None,
        current_bio: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compute all Instagram metrics
        
        Returns a dictionary with all calculated metrics
        """
        # Account stage
        account_stage, account_stage_az = InstagramMetrics.determine_account_stage(followers)
        
        # Ratios and rates
        following_ratio = InstagramMetrics.compute_following_ratio(followers, following)
        posts_per_follower = InstagramMetrics.compute_posts_per_follower(posts, followers)
        engagement_rate = InstagramMetrics.compute_engagement_rate(
            followers, posts, account_stage, posting_frequency
        )
        
        # Normalized frequency
        posting_frequency_text = InstagramMetrics.normalize_posting_frequency(posting_frequency)
        
        return {
            "username": username,
            "followers": followers,
            "following": following,
            "posts": posts,
            "niche": niche or "Ümumi",
            "current_bio": current_bio or "",
            "account_stage": account_stage,
            "account_stage_az": account_stage_az,
            "following_ratio": following_ratio,
            "posts_per_follower": posts_per_follower,
            "engagement_rate": engagement_rate,
            "posting_frequency": posting_frequency,
            "posting_frequency_text": posting_frequency_text,
            "computed_at": datetime.now().isoformat()
        }
    
    @staticmethod
    def analyze_post_timestamps(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze post timestamps to find optimal posting times
        
        Args:
            posts: List of post objects with 'timestamp' field (ISO format or Unix timestamp)
        
        Returns:
            Dictionary with posting time analysis
        """
        if not posts or len(posts) == 0:
            return {
                "total_posts": 0,
                "analysis_available": False,
                "message": "No posts available for analysis"
            }
        
        # Parse timestamps
        parsed_times = []
        for post in posts:
            timestamp = post.get('timestamp') or post.get('taken_at') or post.get('created_at')
            if not timestamp:
                continue
            
            try:
                # Try ISO format first
                if isinstance(timestamp, str):
                    if timestamp.isdigit():
                        # Unix timestamp
                        dt = datetime.fromtimestamp(int(timestamp))
                    else:
                        # ISO format
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif isinstance(timestamp, (int, float)):
                    # Unix timestamp
                    dt = datetime.fromtimestamp(timestamp)
                else:
                    continue
                
                parsed_times.append(dt)
            except (ValueError, TypeError, OSError):
                continue
        
        if len(parsed_times) == 0:
            return {
                "total_posts": len(posts),
                "analysis_available": False,
                "message": "Could not parse post timestamps"
            }
        
        # Extract hours and days of week
        hours = [dt.hour for dt in parsed_times]
        days_of_week = [dt.weekday() for dt in parsed_times]  # 0=Monday, 6=Sunday
        
        # Find most common posting hours
        hour_counter = Counter(hours)
        top_hours = hour_counter.most_common(5)
        
        # Find most common posting days
        day_names = ['Bazar ertəsi', 'Çərşənbə axşamı', 'Çərşənbə', 'Cümə axşamı', 'Cümə', 'Şənbə', 'Bazar']
        day_counter = Counter([day_names[d] for d in days_of_week])
        top_days = day_counter.most_common(3)
        
        # Calculate average posting time
        avg_hour = statistics.mean(hours)
        median_hour = statistics.median(hours)
        
        # Group by time slots
        time_slots = {
            "səhər": [6, 7, 8, 9, 10, 11],
            "gündüz": [12, 13, 14, 15, 16],
            "axşam": [17, 18, 19, 20, 21, 22]
        }
        
        slot_distribution = {}
        for slot_name, slot_hours in time_slots.items():
            count = sum(1 for h in hours if h in slot_hours)
            slot_distribution[slot_name] = {
                "count": count,
                "percentage": round((count / len(hours)) * 100, 1) if len(hours) > 0 else 0
            }
        
        # Find optimal posting times (most common + engagement-friendly times)
        optimal_times = []
        for hour, count in top_hours[:3]:
            hour_str = f"{hour:02d}:00"
            optimal_times.append({
                "time": hour_str,
                "frequency": count,
                "percentage": round((count / len(hours)) * 100, 1) if len(hours) > 0 else 0,
                "reason": f"Ən çox bu saatda post paylaşılıb ({count} dəfə)"
            })
        
        # Calculate posting frequency (average days between posts)
        if len(parsed_times) > 1:
            sorted_times = sorted(parsed_times)
            time_diffs = []
            for i in range(1, len(sorted_times)):
                diff = (sorted_times[i] - sorted_times[i-1]).total_seconds() / 86400  # days
                if diff > 0:
                    time_diffs.append(diff)
            
            avg_days_between = statistics.mean(time_diffs) if time_diffs else 0
            median_days_between = statistics.median(time_diffs) if time_diffs else 0
        else:
            avg_days_between = 0
            median_days_between = 0
        
        return {
            "total_posts": len(posts),
            "analyzed_posts": len(parsed_times),
            "analysis_available": True,
            "optimal_posting_times": optimal_times,
            "most_active_days": [{"day": day, "count": count} for day, count in top_days],
            "time_slot_distribution": slot_distribution,
            "average_posting_hour": round(avg_hour, 1),
            "median_posting_hour": round(median_hour, 1),
            "average_days_between_posts": round(avg_days_between, 1),
            "median_days_between_posts": round(median_days_between, 1),
            "posting_consistency": "Yüksək" if avg_days_between < 2 else "Orta" if avg_days_between < 5 else "Aşağı",
            "analysis_period": {
                "first_post": min(parsed_times).isoformat() if parsed_times else None,
                "last_post": max(parsed_times).isoformat() if parsed_times else None,
                "days_span": (max(parsed_times) - min(parsed_times)).days if len(parsed_times) > 1 else 0
            }
        }

