"""
Instagram Rule Engine

Deterministic rules that trigger recommendations based on metrics.
No AI guessing - pure business logic.
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class RuleResult:
    """Result of a triggered rule"""
    rule_id: str
    severity: str  # "critical", "warning", "info"
    category: str  # "bio", "content", "posting", "engagement", "growth"
    message: str
    recommendation: str
    metrics_used: Dict[str, Any]


class InstagramRuleEngine:
    """Rule engine for Instagram profile analysis"""
    
    # Fixed optimal posting times based on Azerbaijani timezone (GMT+4) and Instagram algorithm
    OPTIMAL_POSTING_TIMES = {
        "weekday_peak": {
            "time": "18:00",
            "score": 95,
            "reason": "İş saatları bitdikdən sonra peak engagement dövrü"
        },
        "weekday_lunch": {
            "time": "13:00",
            "score": 85,
            "reason": "Nahar fasiləsi zamanı istifadəçilər aktivdir"
        },
        "weekday_morning": {
            "time": "08:00",
            "score": 75,
            "reason": "Səhər işə gedərkən Instagram yoxlaması"
        },
        "weekend_morning": {
            "time": "10:00",
            "score": 90,
            "reason": "Həftə sonu səhər rahat vaxt"
        },
        "weekend_evening": {
            "time": "20:00",
            "score": 88,
            "reason": "Həftə sonu axşam sosial media peak saatı"
        }
    }
    
    # Fixed content mix percentages based on Instagram best practices
    CONTENT_MIX_TEMPLATES = {
        "starter": {
            "educational": 35,
            "entertaining": 30,
            "promotional": 10,
            "behind_scenes": 15,
            "user_generated": 10
        },
        "growing": {
            "educational": 30,
            "entertaining": 25,
            "promotional": 15,
            "behind_scenes": 20,
            "user_generated": 10
        },
        "established": {
            "educational": 25,
            "entertaining": 25,
            "promotional": 20,
            "behind_scenes": 20,
            "user_generated": 10
        },
        "influencer": {
            "educational": 20,
            "entertaining": 25,
            "promotional": 25,
            "behind_scenes": 15,
            "user_generated": 15
        }
    }
    
    # Fixed posting frequency recommendations
    POSTING_FREQUENCY_RECOMMENDATIONS = {
        "starter": {
            "posts_per_week": "3-4 post",
            "stories_per_day": "2-3 story",
            "reels_per_week": "2-3 reels"
        },
        "growing": {
            "posts_per_week": "4-5 post",
            "stories_per_day": "3-4 story",
            "reels_per_week": "3-4 reels"
        },
        "established": {
            "posts_per_week": "5-7 post",
            "stories_per_day": "4-6 story",
            "reels_per_week": "4-5 reels"
        },
        "influencer": {
            "posts_per_week": "7+ post",
            "stories_per_day": "6-10 story",
            "reels_per_week": "5-7 reels"
        }
    }
    
    def __init__(self, metrics: Dict[str, Any]):
        """Initialize rule engine with computed metrics"""
        self.metrics = metrics
        self.triggered_rules: List[RuleResult] = []
    
    def evaluate_all_rules(self) -> List[RuleResult]:
        """Evaluate all rules and return triggered ones"""
        self.triggered_rules = []
        
        # Bio rules
        self._evaluate_bio_rules()
        
        # Content strategy rules
        self._evaluate_content_rules()
        
        # Posting frequency rules
        self._evaluate_posting_rules()
        
        # Engagement rules
        self._evaluate_engagement_rules()
        
        # Growth rules
        self._evaluate_growth_rules()
        
        return self.triggered_rules
    
    def _evaluate_bio_rules(self):
        """Evaluate bio-related rules"""
        bio = self.metrics.get("current_bio", "")
        
        if not bio or len(bio) < 20:
            self.triggered_rules.append(RuleResult(
                rule_id="bio_empty_or_short",
                severity="critical",
                category="bio",
                message="Bio boş və ya çox qısadır",
                recommendation="150 simvola qədər cəlbedici bio yaz, emojilər və call-to-action əlavə et",
                metrics_used={"bio_length": len(bio)}
            ))
        
        if bio and len(bio) > 150:
            self.triggered_rules.append(RuleResult(
                rule_id="bio_too_long",
                severity="warning",
                category="bio",
                message="Bio çox uzundur",
                recommendation="Bio-nu 150 simvola qısalt, ən vacib məlumatları saxla",
                metrics_used={"bio_length": len(bio)}
            ))
    
    def _evaluate_content_rules(self):
        """Evaluate content strategy rules"""
        posts = self.metrics.get("posts", 0)
        followers = self.metrics.get("followers", 0)
        posts_per_follower = self.metrics.get("posts_per_follower", 0)
        
        if posts < 9:
            self.triggered_rules.append(RuleResult(
                rule_id="insufficient_posts",
                severity="critical",
                category="content",
                message="Post sayı çox azdır (minimum 9 post olmalıdır)",
                recommendation="Profili cəlbedici etmək üçün ən azı 9 post paylaş",
                metrics_used={"posts": posts}
            ))
        
        if followers > 100 and posts_per_follower < 0.01:
            self.triggered_rules.append(RuleResult(
                rule_id="low_content_density",
                severity="warning",
                category="content",
                message="Followers sayına görə çox az post var",
                recommendation="Daha çox content paylaş, audit etməyə başla",
                metrics_used={"posts_per_follower": posts_per_follower}
            ))
    
    def _evaluate_posting_rules(self):
        """Evaluate posting frequency rules"""
        posting_freq = self.metrics.get("posting_frequency", "")
        account_stage = self.metrics.get("account_stage", "starter")
        
        if posting_freq in ['1-2']:
            self.triggered_rules.append(RuleResult(
                rule_id="posting_too_infrequent",
                severity="warning",
                category="posting",
                message="Paylaşım tezliyi çox azdır",
                recommendation=f"Hesab mərhələniz üçün optimal: {self.POSTING_FREQUENCY_RECOMMENDATIONS[account_stage]['posts_per_week']}",
                metrics_used={"posting_frequency": posting_freq, "account_stage": account_stage}
            ))
        
        if posting_freq in ['2plus', 'daily'] and account_stage in ['starter', 'growing']:
            self.triggered_rules.append(RuleResult(
                rule_id="posting_too_frequent_for_stage",
                severity="info",
                category="posting",
                message="Paylaşım tezliyi hesab mərhələsinə görə çox yüksəkdir",
                recommendation="Keyfiyyəti qurban vermədən tezliyi azalt, daha yaxşı engagement əldə edə bilərsən",
                metrics_used={"posting_frequency": posting_freq, "account_stage": account_stage}
            ))
    
    def _evaluate_engagement_rules(self):
        """Evaluate engagement-related rules"""
        engagement_rate = self.metrics.get("engagement_rate", 0)
        account_stage = self.metrics.get("account_stage", "starter")
        
        # Expected engagement ranges by stage
        expected_ranges = {
            "starter": (4.0, 7.0),
            "growing": (3.0, 5.0),
            "established": (2.0, 4.0),
            "influencer": (1.5, 3.5)
        }
        
        min_expected, max_expected = expected_ranges.get(account_stage, (2.0, 5.0))
        
        if engagement_rate < min_expected:
            self.triggered_rules.append(RuleResult(
                rule_id="low_engagement_rate",
                severity="warning",
                category="engagement",
                message=f"Engagement rate aşağıdır (hesablanmış: {engagement_rate}%, gözlənilən: {min_expected}-{max_expected}%)",
                recommendation="Audience ilə daha çox interact et, suallar ver, story-lərdə polls istifadə et",
                metrics_used={"engagement_rate": engagement_rate, "expected_range": f"{min_expected}-{max_expected}%"}
            ))
        
        following_ratio = self.metrics.get("following_ratio", 0)
        if following_ratio > 2.0:
            self.triggered_rules.append(RuleResult(
                rule_id="high_following_ratio",
                severity="warning",
                category="engagement",
                message=f"Following/Followers nisbəti çox yüksəkdir ({following_ratio})",
                recommendation="Following sayını azalt (unfollow users), profil etibarlılığı artır",
                metrics_used={"following_ratio": following_ratio}
            ))
    
    def _evaluate_growth_rules(self):
        """Evaluate growth-related rules"""
        followers = self.metrics.get("followers", 0)
        account_stage = self.metrics.get("account_stage", "starter")
        
        # Growth milestones
        milestones = {
            "starter": (1000, "İlk 1K follower hədəfi"),
            "growing": (10000, "10K milestone - verified badge üçün uyğunluq"),
            "established": (100000, "100K milestone - influencer status"),
            "influencer": (1000000, "1M milestone - mega influencer")
        }
        
        next_milestone, milestone_desc = milestones.get(account_stage, (1000, "Növbəti hədəf"))
        
        remaining = next_milestone - followers
        if remaining > 0:
            self.triggered_rules.append(RuleResult(
                rule_id="growth_milestone_target",
                severity="info",
                category="growth",
                message=f"Növbəti hədəfə qədər {remaining:,} follower qalıb",
                recommendation=f"{milestone_desc}. Konsistent content və engagement strategiyası izlə",
                metrics_used={"current_followers": followers, "next_milestone": next_milestone}
            ))
    
    def get_content_strategy(self) -> Dict[str, Any]:
        """Get fixed content strategy based on account stage"""
        account_stage = self.metrics.get("account_stage", "starter")
        
        return {
            "content_mix": self.CONTENT_MIX_TEMPLATES[account_stage],
            "post_frequency": self.POSTING_FREQUENCY_RECOMMENDATIONS[account_stage]["posts_per_week"],
            "story_frequency": self.POSTING_FREQUENCY_RECOMMENDATIONS[account_stage]["stories_per_day"],
            "reels_frequency": self.POSTING_FREQUENCY_RECOMMENDATIONS[account_stage]["reels_per_week"],
            "content_pillars": self._get_content_pillars()
        }
    
    def _get_content_pillars(self) -> List[str]:
        """Get content pillars based on niche"""
        niche = self.metrics.get("niche", "").lower()
        
        # Niche-specific content pillars
        pillars_map = {
            "fashion": ["Gündəlik kombinlər", "Trend təhlili", "Stil məsləhətləri", "Moda tarixi"],
            "tech": ["Məhsul icmalları", "Texnoloji xəbərlər", "Tutorial-lar", "Tips & Tricks"],
            "food": ["Reseptlər", "Food photography", "Restaurant review", "Kulinar məsləhətləri"],
            "fitness": ["Workout routines", "Qidalanma", "Motivasiya", "Progress tracking"],
            "business": ["Biznes məsləhətləri", "Entrepreneurship", "Productivity", "Success stories"]
        }
        
        # Check if niche matches any key
        for key, pillars in pillars_map.items():
            if key in niche:
                return pillars
        
        # Default generic pillars
        return ["Əsas content", "Interaktiv content", "Behind-the-scenes", "Community content"]
    
    def get_posting_schedule(self) -> Dict[str, Any]:
        """Get fixed posting schedule (no AI guessing)"""
        return {
            "weekdays": {
                "morning": {
                    "time_range": "06:00-09:00",
                    "best_time": self.OPTIMAL_POSTING_TIMES["weekday_morning"]["time"],
                    "effectiveness": self.OPTIMAL_POSTING_TIMES["weekday_morning"]["reason"]
                },
                "afternoon": {
                    "time_range": "12:00-14:00",
                    "best_time": self.OPTIMAL_POSTING_TIMES["weekday_lunch"]["time"],
                    "effectiveness": self.OPTIMAL_POSTING_TIMES["weekday_lunch"]["reason"]
                },
                "evening": {
                    "time_range": "17:00-20:00",
                    "best_time": self.OPTIMAL_POSTING_TIMES["weekday_peak"]["time"],
                    "effectiveness": self.OPTIMAL_POSTING_TIMES["weekday_peak"]["reason"]
                },
                "best_time": self.OPTIMAL_POSTING_TIMES["weekday_peak"]["time"],
                "best_time_reason": self.OPTIMAL_POSTING_TIMES["weekday_peak"]["reason"]
            },
            "weekend": {
                "best_time": self.OPTIMAL_POSTING_TIMES["weekend_morning"]["time"],
                "alternative_times": [
                    self.OPTIMAL_POSTING_TIMES["weekend_morning"]["time"],
                    self.OPTIMAL_POSTING_TIMES["weekend_evening"]["time"]
                ],
                "best_time_reason": self.OPTIMAL_POSTING_TIMES["weekend_morning"]["reason"]
            },
            "story_times": ["09:00", "14:00", "20:00"],
            "top_3_best_times": [
                {
                    "time": self.OPTIMAL_POSTING_TIMES["weekday_peak"]["time"],
                    "day_type": "Həftə içi",
                    "effectiveness_score": f"{self.OPTIMAL_POSTING_TIMES['weekday_peak']['score']}%",
                    "reason": self.OPTIMAL_POSTING_TIMES["weekday_peak"]["reason"]
                },
                {
                    "time": self.OPTIMAL_POSTING_TIMES["weekend_morning"]["time"],
                    "day_type": "Həftə sonu",
                    "effectiveness_score": f"{self.OPTIMAL_POSTING_TIMES['weekend_morning']['score']}%",
                    "reason": self.OPTIMAL_POSTING_TIMES["weekend_morning"]["reason"]
                },
                {
                    "time": self.OPTIMAL_POSTING_TIMES["weekend_evening"]["time"],
                    "day_type": "Həftə sonu",
                    "effectiveness_score": f"{self.OPTIMAL_POSTING_TIMES['weekend_evening']['score']}%",
                    "reason": self.OPTIMAL_POSTING_TIMES["weekend_evening"]["reason"]
                }
            ]
        }
    
    def get_hashtag_recommendations(self) -> Dict[str, Any]:
        """
        Get niche-based hashtag recommendations
        Note: This provides guidance, not AI-generated hashtags
        Real hashtag research should be done via competitor analysis or Apify scraping
        """
        niche = self.metrics.get("niche", "").lower()
        account_stage = self.metrics.get("account_stage", "starter")
        
        # Niche-based hashtag guidance
        niche_guidance = {
            "fashion": {
                "focus_areas": ["Style trends", "Outfit ideas", "Fashion brands", "Seasonal fashion"],
                "research_tips": "Fashion və style hashtag-larını araşdır, top fashion influencer-lərin hashtag-larını izlə"
            },
            "tech": {
                "focus_areas": ["Technology news", "Gadgets", "Programming", "Innovation"],
                "research_tips": "Tech və innovation hashtag-larını araşdır, tech community-ləri izlə"
            },
            "food": {
                "focus_areas": ["Recipes", "Food photography", "Restaurants", "Cooking"],
                "research_tips": "Food və cooking hashtag-larını araşdır, food blogger-ləri izlə"
            },
            "fitness": {
                "focus_areas": ["Workout", "Nutrition", "Fitness motivation", "Health"],
                "research_tips": "Fitness və health hashtag-larını araşdır, fitness influencer-ləri izlə"
            },
            "business": {
                "focus_areas": ["Entrepreneurship", "Business tips", "Productivity", "Success"],
                "research_tips": "Business və entrepreneur hashtag-larını araşdır, business coaches izlə"
            }
        }
        
        # Find matching niche guidance
        guidance = None
        for key, value in niche_guidance.items():
            if key in niche:
                guidance = value
                break
        
        if not guidance:
            guidance = {
                "focus_areas": ["Your niche", "Community", "Engagement", "Quality content"],
                "research_tips": "Niche-nə uyğun hashtag-ları araşdır, rəqiblərin hashtag-larını analiz et"
            }
        
        # Stage-based strategy
        strategy_by_stage = {
            "starter": {
                "competition_mix": "60% az rəqabət (1k-10k), 30% orta (10k-100k), 10% yüksək (100k+)",
                "count_recommendation": "20-30 hashtag istifadə et",
                "tips": [
                    "Az rəqabətli hashtag-lara fokuslan",
                    "Mikro-niche hashtag-lar tap",
                    "Location-based hashtag-lar əlavə et"
                ]
            },
            "growing": {
                "competition_mix": "40% az rəqabət, 40% orta, 20% yüksək",
                "count_recommendation": "25-30 hashtag istifadə et",
                "tips": [
                    "Orta rəqabətli hashtag-lara keç",
                    "Branded hashtag yaratmağa başla",
                    "Community hashtag-larına qoşul"
                ]
            },
            "established": {
                "competition_mix": "20% az rəqabət, 50% orta, 30% yüksək",
                "count_recommendation": "20-30 hashtag istifadə et",
                "tips": [
                    "Yüksək rəqabətli hashtag-larda da iştirak et",
                    "Branded hashtag-ını promot et",
                    "Trending hashtag-ları izlə"
                ]
            },
            "influencer": {
                "competition_mix": "10% az rəqabət, 40% orta, 50% yüksək",
                "count_recommendation": "15-25 hashtag (keyfiyyət > kəmiyyət)",
                "tips": [
                    "Premium və yüksək rəqabətli hashtag-lara fokuslan",
                    "Öz branded hashtag-ını istifadə et",
                    "Industry-specific hashtag-larda lider ol"
                ]
            }
        }
        
        stage_strategy = strategy_by_stage.get(account_stage, strategy_by_stage["starter"])
        
        return {
            "note": "Hashtag seçimi real research tələb edir. AI guess edilmir.",
            "recommendation": "Rəqiblərin və niche influencer-lərinin hashtag-larını analiz et",
            "niche_focus_areas": guidance["focus_areas"],
            "research_tips": guidance["research_tips"],
            "competition_mix": stage_strategy["competition_mix"],
            "count_recommendation": stage_strategy["count_recommendation"],
            "strategy_tips": stage_strategy["tips"],
            "tools": [
                "Instagram search (hashtag-ı axtarıb post count gör)",
                "Rəqib profillər (top posts hansı hashtag istifadə edir)",
                "Hashtag generator tools (DisplayPurposes, All Hashtag)",
                "Apify scraping (avtomatik competitor hashtag analizi)"
            ]
        }

