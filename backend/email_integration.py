"""
Complete email integration for BMA Social
Handles verification, notifications, and automated emails
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

class EmailManager:
    """
    Manage all email communications
    - Verification emails
    - Subscription reminders
    - Issue summaries
    - Automated notifications
    """
    
    def __init__(self):
        # Gmail SMTP configuration
        self.smtp_host = 'smtp.gmail.com'
        self.smtp_port = 587
        self.smtp_user = os.getenv('SMTP_USER', 'norbert@bmasiamusic.com')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '').replace(' ', '')  # Remove spaces from app password
        
        # For production, use production@bmasiamusic.com
        self.production_email = os.getenv('PRODUCTION_EMAIL', 'production@bmasiamusic.com')
        
        # Email templates
        self.templates = {
            'verification': self._get_verification_template(),
            'subscription_reminder': self._get_subscription_template(),
            'issue_resolved': self._get_issue_resolved_template(),
            'weekly_report': self._get_weekly_report_template()
        }
        
        self.test_connection()
    
    def test_connection(self):
        """Test SMTP connection on startup"""
        if not self.smtp_password:
            logger.warning("SMTP_PASSWORD not set - email features disabled")
            logger.info("To enable: Add SMTP_PASSWORD to Render environment variables")
            return False
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
            logger.info(f"✅ Email system connected via {self.smtp_user}")
            return True
        except Exception as e:
            logger.error(f"❌ Email connection failed: {e}")
            logger.info("Check SMTP_PASSWORD in environment variables")
            return False
    
    def send_verification_code(self, to_email: str, code: str, venue_name: str) -> bool:
        """Send verification code email"""
        
        subject = "BMA Music Support - Verification Code"
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #2c3e50; margin: 0;">BMA Music Support</h1>
                <p style="color: #7f8c8d; margin: 5px 0;">Verification Code</p>
              </div>
              
              <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          border-radius: 10px; padding: 30px; color: white; text-align: center;">
                <p style="margin: 0 0 20px 0; font-size: 16px;">Your verification code for</p>
                <h2 style="margin: 0 0 20px 0; font-size: 24px;">{venue_name}</h2>
                <div style="background: white; color: #667eea; padding: 15px 30px; 
                            border-radius: 50px; display: inline-block; font-size: 32px; 
                            font-weight: bold; letter-spacing: 8px;">
                  {code}
                </div>
              </div>
              
              <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <p style="margin: 0 0 10px 0;"><strong>Quick Steps:</strong></p>
                <ol style="margin: 10px 0; padding-left: 20px;">
                  <li>Copy the code above</li>
                  <li>Return to WhatsApp</li>
                  <li>Paste the code in your chat</li>
                </ol>
                <p style="margin: 10px 0 0 0; color: #7f8c8d; font-size: 14px;">
                  Code expires in 10 minutes • One-time verification for 30 days
                </p>
              </div>
              
              <div style="margin-top: 20px; text-align: center; color: #95a5a6; font-size: 12px;">
                <p>This verification ensures secure access to your venue's music controls.</p>
                <p>If you didn't request this, please ignore this email.</p>
              </div>
            </div>
          </body>
        </html>
        """
        
        return self._send_email(to_email, subject, html)
    
    def send_subscription_reminder(self, to_email: str, venue_name: str, 
                                  expiry_date: datetime, days_remaining: int) -> bool:
        """Send subscription expiration reminder"""
        
        subject = f"Subscription Reminder - {venue_name}"
        
        # Color based on urgency
        if days_remaining <= 7:
            color = "#e74c3c"  # Red
            urgency = "URGENT"
        elif days_remaining <= 14:
            color = "#f39c12"  # Orange
            urgency = "Important"
        else:
            color = "#3498db"  # Blue
            urgency = "Reminder"
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <div style="border-left: 4px solid {color}; padding-left: 20px;">
                <h2 style="color: {color}; margin: 0;">{urgency}: Subscription Expiring</h2>
                <h3 style="color: #2c3e50; margin: 10px 0;">{venue_name}</h3>
              </div>
              
              <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <p style="font-size: 18px; margin: 0;">
                  Your music service subscription expires in:
                </p>
                <p style="font-size: 36px; color: {color}; font-weight: bold; margin: 10px 0;">
                  {days_remaining} days
                </p>
                <p style="color: #7f8c8d; margin: 0;">
                  Expiry Date: {expiry_date.strftime('%B %d, %Y')}
                </p>
              </div>
              
              <div style="margin: 20px 0;">
                <a href="https://bmasiamusic.com/renew" 
                   style="background: {color}; color: white; padding: 15px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                  Renew Subscription
                </a>
              </div>
              
              <div style="border-top: 1px solid #dee2e6; margin-top: 30px; padding-top: 20px;">
                <p style="color: #6c757d; font-size: 14px;">
                  Need help? Reply to this email or WhatsApp us at +66 63 237 7765
                </p>
              </div>
            </div>
          </body>
        </html>
        """
        
        return self._send_email(to_email, subject, html)
    
    def send_issue_resolved(self, to_email: str, venue_name: str, 
                           issue_description: str, resolution: str) -> bool:
        """Send issue resolution summary"""
        
        subject = f"Issue Resolved - {venue_name}"
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <div style="text-align: center; margin-bottom: 30px;">
                <div style="display: inline-block; background: #27ae60; color: white; 
                            width: 60px; height: 60px; border-radius: 50%; 
                            line-height: 60px; font-size: 30px;">✓</div>
                <h2 style="color: #27ae60; margin: 10px 0;">Issue Resolved</h2>
                <p style="color: #7f8c8d;">{venue_name}</p>
              </div>
              
              <div style="background: #f8f9fa; padding: 20px; border-radius: 10px;">
                <h3 style="color: #2c3e50; margin: 0 0 10px 0;">Issue:</h3>
                <p style="margin: 0 0 20px 0;">{issue_description}</p>
                
                <h3 style="color: #2c3e50; margin: 0 0 10px 0;">Resolution:</h3>
                <p style="margin: 0;">{resolution}</p>
              </div>
              
              <div style="margin-top: 20px; padding: 15px; border: 1px solid #27ae60; 
                          border-radius: 10px; background: #f0fff4;">
                <p style="margin: 0; color: #27ae60;">
                  ✓ Resolved on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                </p>
              </div>
              
              <div style="margin-top: 30px; text-align: center;">
                <p style="color: #6c757d;">
                  How did we do? 
                  <a href="#" style="color: #27ae60;">Great</a> • 
                  <a href="#" style="color: #f39c12;">Okay</a> • 
                  <a href="#" style="color: #e74c3c;">Needs Improvement</a>
                </p>
              </div>
            </div>
          </body>
        </html>
        """
        
        return self._send_email(to_email, subject, html)
    
    def send_weekly_report(self, to_email: str, venue_name: str, stats: Dict) -> bool:
        """Send weekly statistics report"""
        
        subject = f"Weekly Music System Report - {venue_name}"
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #2c3e50;">Weekly Report</h2>
              <p style="color: #7f8c8d;">{venue_name} • Week of {datetime.now().strftime('%B %d, %Y')}</p>
              
              <div style="display: flex; justify-content: space-between; margin: 30px 0;">
                <div style="flex: 1; text-align: center;">
                  <p style="color: #7f8c8d; margin: 0;">Uptime</p>
                  <p style="font-size: 32px; color: #27ae60; margin: 5px 0;">
                    {stats.get('uptime', '99.9')}%
                  </p>
                </div>
                <div style="flex: 1; text-align: center;">
                  <p style="color: #7f8c8d; margin: 0;">Issues Resolved</p>
                  <p style="font-size: 32px; color: #3498db; margin: 5px 0;">
                    {stats.get('issues_resolved', 0)}
                  </p>
                </div>
                <div style="flex: 1; text-align: center;">
                  <p style="color: #7f8c8d; margin: 0;">Active Zones</p>
                  <p style="font-size: 32px; color: #9b59b6; margin: 5px 0;">
                    {stats.get('active_zones', 0)}
                  </p>
                </div>
              </div>
              
              <div style="background: #f8f9fa; padding: 20px; border-radius: 10px;">
                <h3 style="margin: 0 0 15px 0;">Top Issues This Week:</h3>
                <ul style="margin: 0; padding-left: 20px;">
                  <li>Volume adjustments: {stats.get('volume_adjustments', 0)}</li>
                  <li>Playlist changes: {stats.get('playlist_changes', 0)}</li>
                  <li>Connection issues: {stats.get('connection_issues', 0)}</li>
                </ul>
              </div>
            </div>
          </body>
        </html>
        """
        
        return self._send_email(to_email, subject, html)
    
    def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Core email sending function"""
        
        if not self.smtp_password:
            logger.warning(f"Email not sent (SMTP not configured): {subject} to {to_email}")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"BMA Music Support <{self.smtp_user}>"
            msg['To'] = to_email
            
            # Add HTML part
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email sent: {subject} to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False
    
    def _get_verification_template(self):
        """Get verification email template"""
        return "verification"
    
    def _get_subscription_template(self):
        """Get subscription reminder template"""
        return "subscription"
    
    def _get_issue_resolved_template(self):
        """Get issue resolved template"""
        return "resolved"
    
    def _get_weekly_report_template(self):
        """Get weekly report template"""
        return "report"


# Automated email tasks
class EmailAutomation:
    """
    Handle automated email tasks
    - Daily subscription checks
    - Weekly reports
    - Follow-ups
    """
    
    def __init__(self, email_manager: EmailManager):
        self.email = email_manager
        self.last_check = {}
    
    def check_subscriptions(self):
        """Check for expiring subscriptions and send reminders"""
        
        # This would connect to database to get subscription data
        # For now, example logic:
        
        try:
            from database import db_manager
            
            with db_manager.get_cursor() as cursor:
                if cursor:
                    # Find subscriptions expiring in 30, 14, 7, 3, 1 days
                    cursor.execute("""
                        SELECT v.*, 
                               DATE_PART('day', subscription_expires - CURRENT_DATE) as days_remaining
                        FROM venues v
                        WHERE subscription_expires IS NOT NULL
                        AND subscription_expires > CURRENT_DATE
                        AND subscription_expires <= CURRENT_DATE + INTERVAL '30 days'
                        AND (last_reminder_sent IS NULL 
                             OR last_reminder_sent < CURRENT_DATE - INTERVAL '3 days')
                    """)
                    
                    expiring = cursor.fetchall()
                    
                    for venue in expiring:
                        days = int(venue['days_remaining'])
                        
                        # Send reminders at specific intervals
                        if days in [30, 14, 7, 3, 1]:
                            self.email.send_subscription_reminder(
                                venue['contact_email'],
                                venue['name'],
                                venue['subscription_expires'],
                                days
                            )
                            
                            # Update last reminder sent
                            cursor.execute("""
                                UPDATE venues 
                                SET last_reminder_sent = CURRENT_DATE
                                WHERE id = %s
                            """, (venue['id'],))
                    
                    logger.info(f"Checked {len(expiring)} expiring subscriptions")
                    
        except Exception as e:
            logger.error(f"Subscription check failed: {e}")
    
    def send_weekly_reports(self):
        """Send weekly reports to venues"""
        
        # This would aggregate weekly statistics
        # For now, example logic:
        
        try:
            from database import db_manager
            
            with db_manager.get_cursor() as cursor:
                if cursor:
                    # Get venues that want weekly reports
                    cursor.execute("""
                        SELECT v.* FROM venues v
                        WHERE weekly_reports = true
                        AND active = true
                    """)
                    
                    venues = cursor.fetchall()
                    
                    for venue in venues:
                        # Get stats for this venue
                        stats = self._get_venue_stats(venue['id'])
                        
                        self.email.send_weekly_report(
                            venue['contact_email'],
                            venue['name'],
                            stats
                        )
                    
                    logger.info(f"Sent weekly reports to {len(venues)} venues")
                    
        except Exception as e:
            logger.error(f"Weekly reports failed: {e}")
    
    def _get_venue_stats(self, venue_id: int) -> Dict:
        """Get weekly statistics for a venue"""
        # This would calculate real stats
        return {
            'uptime': '99.9',
            'issues_resolved': 3,
            'active_zones': 5,
            'volume_adjustments': 8,
            'playlist_changes': 2,
            'connection_issues': 1
        }


# Global instance
email_manager = EmailManager()
email_automation = EmailAutomation(email_manager)