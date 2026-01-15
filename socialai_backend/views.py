from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


def privacy_policy(request):
    """Privacy Policy page for Meta compliance"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Privacy Policy - Timera</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; line-height: 1.6; }
            h1 { color: #1877f2; }
            h2 { color: #333; margin-top: 30px; }
            p { line-height: 1.6; }
            ul { margin: 10px 0; }
            li { margin: 5px 0; }
            .important { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>Privacy Policy - Timera</h1>
        <p><strong>Last Updated:</strong> January 15, 2026</p>
        
        <h2>1. Information We Collect</h2>
        <p>Timera collects the following information from users:</p>
        <ul>
            <li>Personal information (name, email address)</li>
            <li>Company information (company name, industry, size)</li>
            <li>Facebook/Instagram account information (only encrypted access tokens)</li>
            <li>Posts and content you create and approve through our platform</li>
            <li>Analytics data (aggregated and anonymized)</li>
        </ul>
        
        <h2>2. How We Use Your Information</h2>
        <p>The collected information is used for the following purposes:</p>
        <ul>
            <li>Providing and improving services</li>
            <li>AI-assisted content generation (user review and approval required)</li>
            <li>Managing user accounts and authentication</li>
            <li>Publishing content ONLY after your explicit approval</li>
            <li>Technical support and customer service</li>
            <li>Compliance with legal requirements</li>
        </ul>
        
        <div class="important">
            <strong>⚠️ Important:</strong> AI generates content suggestions, but <strong>you review, edit, and approve</strong> before any post is published. No automated posting occurs without your manual approval.
        </div>
        
        <h2>3. How We Share Your Information</h2>
        <p>We share your information with third parties only in the following cases:</p>
        <ul>
            <li>Service providers (cloud hosting, payment systems)</li>
            <li>AI service providers (OpenAI for content generation - data not used for model training)</li>
            <li>Meta/Facebook/Instagram (only when you explicitly connect and approve actions)</li>
            <li>Legal requirements and court orders</li>
            <li>With your explicit consent</li>
        </ul>
        <p><strong>⚠️ We NEVER share your social media credentials or passwords. Only encrypted access tokens are stored.</strong></p>
        
        <h2>4. Data Security</h2>
        <p>To ensure the security of your information:</p>
        <ul>
            <li>We use encrypted connections (HTTPS/SSL) for all communications</li>
            <li>All access tokens are encrypted at rest and in transit</li>
            <li>Data is stored on secure servers with limited access</li>
            <li>Regular security audits are performed</li>
            <li>Two-factor authentication available for user accounts</li>
        </ul>
        
        <h2>5. User Rights & Control</h2>
        <p>You have full control over your data and accounts:</p>
        <ul>
            <li>Access, correct, or delete your personal information</li>
            <li>Disconnect social media accounts at any time</li>
            <li>Revoke permissions granted to Timera</li>
            <li>Export your data (data portability)</li>
            <li>Object to processing of your information</li>
        </ul>
        <p><strong>You maintain full control over your social media accounts and can revoke access at any time through your Facebook/Instagram settings or our platform.</strong></p>
        
        <h2>6. Data Retention</h2>
        <p>We retain your information as follows:</p>
        <ul>
            <li>Account data: Until account deletion</li>
            <li>Posts and content: Until you delete them or your account</li>
            <li>Rejected posts: Retained for 30 days, then automatically deleted</li>
            <li>Access tokens: Immediately deleted when you disconnect an account</li>
            <li>Analytics data: Aggregated and anonymized for 90 days</li>
        </ul>
        
        <h2>7. Third-Party Services</h2>
        <p>Timera integrates with:</p>
        <ul>
            <li>Meta/Facebook/Instagram: For social media management (subject to their privacy policies)</li>
            <li>OpenAI: For AI content generation (data not used for model training)</li>
            <li>Fal.ai/Ideogram: For image generation</li>
        </ul>
        
        <h2>8. Contact Us</h2>
        <p>For privacy concerns, contact us at: <strong>privacy@timera.az</strong></p>
        <p>For data deletion requests, visit: <a href="https://api.timera.az/user-data-deletion/">https://api.timera.az/user-data-deletion/</a></p>
    </body>
    </html>
    """
    return HttpResponse(html)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def user_data_deletion(request):
    """
    User Data Deletion Callback for Meta compliance
    
    Meta sends a signed request here when a user deletes your app.
    You should delete all data associated with that user.
    """
    
    if request.method == "POST":
        try:
            # Parse the signed request from Meta
            signed_request = request.POST.get('signed_request', '')
            
            # For now, just acknowledge receipt
            # In production, you would:
            # 1. Verify the signed request
            # 2. Extract user ID
            # 3. Delete user's data from your database
            # 4. Return confirmation URL and code
            
            return JsonResponse({
                'url': 'https://api.timera.az/delete_user',
                'confirmation_code': 'timera_deletion_confirmed'
            })
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=400)
    
    # GET request - show information page
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Data Deletion - Timera</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #1877f2; }
            p { line-height: 1.6; }
        </style>
    </head>
    <body>
        <h1>Data Deletion Request - Timera</h1>
        <p>This endpoint handles data deletion requests from Facebook when users remove our app.</p>
        <p>If you want to delete your data, please:</p>
        <ol>
            <li>Log into your Timera account</li>
            <li>Go to Settings</li>
            <li>Disconnect all social accounts</li>
            <li>Delete your account</li>
        </ol>
        <p>For assistance, contact: support@timera.az</p>
    </body>
    </html>
    """
    return HttpResponse(html)


def terms_of_service(request):
    """Terms of Service page for Meta compliance"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Terms of Service - Timera</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; line-height: 1.6; }
            h1 { color: #1877f2; }
            h2 { color: #333; margin-top: 30px; }
            p { line-height: 1.6; }
            ul { margin: 10px 0; }
            li { margin: 5px 0; }
            .important { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>Terms of Service - Timera</h1>
        <p><strong>Last Updated:</strong> January 15, 2026</p>
        
        <h2>1. Acceptance of Terms</h2>
        <p>By accessing and using Timera, you accept and agree to be bound by these Terms of Service. If you do not agree with these terms, please do not use the platform.</p>
        
        <h2>2. Description of Service</h2>
        <p>Timera is an AI-assisted social media management platform. Our services include:</p>
        <ul>
            <li>AI-assisted content generation (user review and approval required)</li>
            <li>Social media post scheduling (manual approval before publishing)</li>
            <li>Multi-platform publishing (user controls all publishing actions)</li>
            <li>Analytics and performance tracking</li>
            <li>Meta Ads campaign management (user oversight required)</li>
        </ul>
        
        <div class="important">
            <strong>⚠️ Important: AI assists, but you decide and approve.</strong>
            <p>AI generates content suggestions - you review, edit, and approve before any post is published. No content is published without your explicit approval. Scheduled posts require manual approval - automated publishing only occurs after you approve.</p>
        </div>
        
        <h2>3. User Responsibilities</h2>
        <p>You are responsible for:</p>
        <ul>
            <li>Maintaining the security of your account credentials</li>
            <li><strong>All content posted through our platform (even if AI-generated, YOU approve it)</strong></li>
            <li>Reviewing all AI-generated content before approval</li>
            <li>Compliance with Facebook, Instagram, and other platform terms of service</li>
            <li>Ensuring you have rights to all content you post</li>
            <li>Verifying content accuracy and appropriateness</li>
        </ul>
        
        <h2>4. AI-Assisted Content & User Control</h2>
        <p><strong>You maintain full control over all content and publishing actions:</strong></p>
        <ul>
            <li>AI generates content suggestions - you review, edit, and approve before any post is published</li>
            <li>No content is published without your explicit approval</li>
            <li>Scheduled posts require manual approval - automated publishing only occurs after you approve</li>
            <li>You have full control to edit, modify, or reject any AI-generated content</li>
            <li>All Meta Ads actions require your authorization and approval</li>
            <li>You are responsible for reviewing all content before it goes live</li>
        </ul>
        
        <h2>5. Meta Platform Integration & User Oversight</h2>
        <p>By connecting your Facebook or Instagram accounts, you authorize Timera to:</p>
        <ul>
            <li>Access your Pages and Instagram Business accounts</li>
            <li><strong>Publish posts on your behalf ONLY after you approve them</strong></li>
            <li>Retrieve engagement metrics and analytics</li>
            <li>Manage messages from your connected accounts (user reads and replies)</li>
        </ul>
        <p><strong>⚠️ Important: No automated posting occurs without your manual review and approval. You maintain full control over what gets published.</strong></p>
        
        <h2>6. Prohibited Activities</h2>
        <p>You may not use Timera to:</p>
        <ul>
            <li>Post spam, fraud, or misleading content</li>
            <li>Violate any laws or third-party rights</li>
            <li>Violate Meta, Facebook, Instagram, or other platform policies</li>
            <li>Compromise platform security or harm the system</li>
            <li>Access other users' accounts without authorization</li>
            <li>Resell or redistribute platform services for commercial purposes</li>
        </ul>
        
        <h2>7. Content Responsibility</h2>
        <p>You are fully responsible for all content created and published through our platform:</p>
        <ul>
            <li>Content must comply with legal and ethical standards</li>
            <li>You must respect copyright and intellectual property</li>
            <li>You cannot create harmful, offensive, or illegal content</li>
            <li>You must not violate third-party rights</li>
            <li><strong>Even though AI generates suggestions, YOU approve and publish - you are responsible</strong></li>
        </ul>
        
        <h2>8. Data and Privacy</h2>
        <p>Your use of Timera is also governed by our Privacy Policy. We encrypt all access tokens and handle your data securely. See our <a href="/privacy-policy/">Privacy Policy</a> for full details.</p>
        
        <h2>9. Service Modifications</h2>
        <p>We reserve the right to modify or discontinue the service at any time with reasonable notice to users.</p>
        
        <h2>10. Limitation of Liability</h2>
        <p>Timera is provided "as is" without warranties. We are not liable for any damages arising from your use of the service. You use the platform at your own risk.</p>
        
        <h2>11. Termination</h2>
        <p>You may terminate your account at any time. We may terminate accounts that violate these terms. Upon termination, your data will be deleted according to our retention policy.</p>
        
        <h2>12. Contact</h2>
        <p>For questions about these Terms, contact us at: <strong>legal@timera.az</strong></p>
    </body>
    </html>
    """
    return HttpResponse(html)



