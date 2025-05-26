"""
Export Service
Handles data export functionality in various formats (CSV, PDF, JSON)
"""
import csv
import json
import io
import sqlite3
from datetime import datetime
from flask import make_response, current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import logging

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting user data in various formats"""
    
    @staticmethod
    def get_user_data_for_export(user_id, include_breaks=True):
        """Get all user data for export"""
        try:
            db_path = current_app.config.get('DATABASE', 'attendance.db')
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get user info
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user_info = cursor.fetchone()
            
            if not user_info:
                return None
            
            # Get attendance records
            cursor.execute('''
                SELECT date, check_in_time, check_out_time, 
                       billable_minutes, has_auto_breaks
                FROM attendance 
                WHERE user_id = ? 
                ORDER BY date DESC
            ''', (user_id,))
            attendance_records = cursor.fetchall()
            
            # Get break records if requested
            break_records = []
            if include_breaks:
                cursor.execute('''
                    SELECT date, start_time, end_time, break_type, duration_minutes
                    FROM breaks 
                    WHERE user_id = ? 
                    ORDER BY date DESC, start_time DESC
                ''', (user_id,))
                break_records = cursor.fetchall()
            
            # Get user settings
            cursor.execute('SELECT * FROM user_settings WHERE user_id = ?', (user_id,))
            user_settings = cursor.fetchone()
            
            conn.close()
            
            return {
                'user_info': dict(user_info),
                'attendance_records': [dict(record) for record in attendance_records],
                'break_records': [dict(record) for record in break_records],
                'user_settings': dict(user_settings) if user_settings else {},
                'export_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user data for export: {str(e)}")
            return None
    
    @staticmethod
    def export_to_csv(user_data, include_breaks=True):
        """Export user data to CSV format"""
        try:
            output = io.StringIO()
            
            # Write user info section
            writer = csv.writer(output)
            writer.writerow(['# Benutzerdaten'])
            writer.writerow(['Benutzername', user_data['user_info'].get('username', '')])
            writer.writerow(['User ID', user_data['user_info'].get('id', '')])
            writer.writerow(['Export Zeitstempel', user_data.get('export_timestamp', '')])
            writer.writerow([])  # Empty row
            
            # Write attendance records
            writer.writerow(['# Anwesenheitsaufzeichnungen'])
            writer.writerow(['Datum', 'Check-In', 'Check-Out', 'Abrechenbare Minuten', 'Auto-Pausen'])
            
            for record in user_data['attendance_records']:
                writer.writerow([
                    record.get('date', ''),
                    record.get('check_in_time', ''),
                    record.get('check_out_time', ''),
                    record.get('billable_minutes', ''),
                    'Ja' if record.get('has_auto_breaks') else 'Nein'
                ])
            
            # Write break records if included
            if include_breaks and user_data['break_records']:
                writer.writerow([])  # Empty row
                writer.writerow(['# Pausenaufzeichnungen'])
                writer.writerow(['Datum', 'Start', 'Ende', 'Typ', 'Dauer (Minuten)'])
                
                for record in user_data['break_records']:
                    writer.writerow([
                        record.get('date', ''),
                        record.get('start_time', ''),
                        record.get('end_time', ''),
                        record.get('break_type', ''),
                        record.get('duration_minutes', '')
                    ])
            
            # Create response
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=zeiterfassung_{user_data["user_info"]["username"]}_{datetime.now().strftime("%Y%m%d")}.csv'
            
            return response
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            return None
    
    @staticmethod
    def export_to_json(user_data):
        """Export user data to JSON format"""
        try:
            # Create clean JSON data
            json_data = {
                'user_info': user_data['user_info'],
                'attendance_records': user_data['attendance_records'],
                'break_records': user_data['break_records'],
                'user_settings': user_data['user_settings'],
                'export_timestamp': user_data['export_timestamp']
            }
            
            json_string = json.dumps(json_data, indent=2, ensure_ascii=False)
            
            response = make_response(json_string)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = f'attachment; filename=zeiterfassung_{user_data["user_info"]["username"]}_{datetime.now().strftime("%Y%m%d")}.json'
            
            return response
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {str(e)}")
            return None
    
    @staticmethod
    def export_to_pdf(user_data, include_breaks=True):
        """Export user data to PDF format"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title = Paragraph(f"Zeiterfassung Export - {user_data['user_info']['username']}", styles['Title'])
            elements.append(title)
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            
            # User information
            user_info_data = [
                ['Benutzername:', user_data['user_info'].get('username', '')],
                ['User ID:', str(user_data['user_info'].get('id', ''))],
                ['Export Zeitstempel:', user_data.get('export_timestamp', '')]
            ]
            
            user_info_table = Table(user_info_data, colWidths=[2*inch, 4*inch])
            user_info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(user_info_table)
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            
            # Attendance records
            if user_data['attendance_records']:
                elements.append(Paragraph("Anwesenheitsaufzeichnungen", styles['Heading2']))
                
                attendance_data = [['Datum', 'Check-In', 'Check-Out', 'Minuten', 'Auto-Pausen']]
                
                for record in user_data['attendance_records']:
                    attendance_data.append([
                        record.get('date', ''),
                        record.get('check_in_time', ''),
                        record.get('check_out_time', ''),
                        str(record.get('billable_minutes', '')),
                        'Ja' if record.get('has_auto_breaks') else 'Nein'
                    ])
                
                attendance_table = Table(attendance_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1*inch, 1*inch])
                attendance_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))
                
                elements.append(attendance_table)
                elements.append(Paragraph("<br/>", styles['Normal']))
            
            # Break records
            if include_breaks and user_data['break_records']:
                elements.append(Paragraph("Pausenaufzeichnungen", styles['Heading2']))
                
                break_data = [['Datum', 'Start', 'Ende', 'Typ', 'Dauer (Min.)']]
                
                for record in user_data['break_records']:
                    break_data.append([
                        record.get('date', ''),
                        record.get('start_time', ''),
                        record.get('end_time', ''),
                        record.get('break_type', ''),
                        str(record.get('duration_minutes', ''))
                    ])
                
                break_table = Table(break_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1*inch, 1*inch])
                break_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))
                
                elements.append(break_table)
            
            doc.build(elements)
            pdf_data = buffer.getvalue()
            buffer.close()
            
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=zeiterfassung_{user_data["user_info"]["username"]}_{datetime.now().strftime("%Y%m%d")}.pdf'
            
            return response
            
        except Exception as e:
            logger.error(f"Error exporting to PDF: {str(e)}")
            return None