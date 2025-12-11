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
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #1877f2; }
            h2 { color: #333; margin-top: 30px; }
            p { line-height: 1.6; }
        </style>
    </head>
    <body>
        <h1>Privacy Policy - Timera</h1>
        <p><strong>Last Updated:</strong> October 23, 2025</p>
        
        <h2>1. Information We Collect</h2>
        <p>We collect information you provide when you connect your social media accounts, including:</p>
        <ul>
            <li>Facebook/Instagram account information</li>
            <li>Access tokens (encrypted)</li>
            <li>Posts and content you create through our platform</li>
        </ul>
        
        <h2>2. How We Use Your Information</h2>
        <p>We use your information to:</p>
        <ul>
            <li>Manage and publish your social media content</li>
            <li>Connect to Facebook and Instagram APIs</li>
            <li>Provide AI-powered content generation</li>
        </ul>
        
        <h2>3. Data Security</h2>
        <p>We encrypt all access tokens and use secure connections for all API communications.</p>
        
        <h2>4. Your Rights</h2>
        <p>You can disconnect your accounts and delete your data at any time through our platform.</p>
        
        <h2>5. Contact Us</h2>
        <p>For privacy concerns, contact us at: support@timera.az</p>
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
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #1877f2; }
            h2 { color: #333; margin-top: 30px; }
            p { line-height: 1.6; }
        </style>
    </head>
    <body>
        <h1>Terms of Service - Timera</h1>
        <p><strong>Last Updated:</strong> October 24, 2025</p>
        
        <h2>1. Acceptance of Terms</h2>
        <p>By accessing and using Timera, you accept and agree to be bound by these Terms of Service.</p>
        
        <h2>2. Description of Service</h2>
        <p>Timera is an AI-powered social media management platform that helps you:</p>
        <ul>
            <li>Generate content for social media posts</li>
            <li>Manage and publish content to Facebook and Instagram</li>
            <li>Schedule and automate social media posting</li>
        </ul>
        
        <h2>3. User Responsibilities</h2>
        <p>You are responsible for:</p>
        <ul>
            <li>Maintaining the security of your account credentials</li>
            <li>All content posted through our platform</li>
            <li>Compliance with Facebook and Instagram's terms of service</li>
            <li>Ensuring you have rights to all content you post</li>
        </ul>
        
        <h2>4. Facebook and Instagram Integration</h2>
        <p>By connecting your Facebook or Instagram accounts, you authorize Timera to:</p>
        <ul>
            <li>Access your Pages and Instagram Business accounts</li>
            <li>Publish posts on your behalf</li>
            <li>Retrieve engagement metrics</li>
        </ul>
        
        <h2>5. Prohibited Activities</h2>
        <p>You may not use Timera to:</p>
        <ul>
            <li>Post spam or misleading content</li>
            <li>Violate any laws or third-party rights</li>
            <li>Engage in automated posting that violates platform policies</li>
        </ul>
        
        <h2>6. Data and Privacy</h2>
        <p>Your use of Timera is also governed by our Privacy Policy. We encrypt all access tokens and handle your data securely.</p>
        
        <h2>7. Service Modifications</h2>
        <p>We reserve the right to modify or discontinue the service at any time with reasonable notice.</p>
        
        <h2>8. Limitation of Liability</h2>
        <p>Timera is provided "as is" without warranties. We are not liable for any damages arising from your use of the service.</p>
        
        <h2>9. Termination</h2>
        <p>You may terminate your account at any time. We may terminate accounts that violate these terms.</p>
        
        <h2>10. Contact</h2>
        <p>For questions about these Terms, contact us at: support@timera.az</p>
    </body>
    </html>
    """
    return HttpResponse(html)



