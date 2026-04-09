from django.core.management.base import BaseCommand
from organizations.models import Organization


class Command(BaseCommand):
    help = 'Populate database with insurance companies'
    
    def handle(self, *args, **options):
        # Clear existing insurance companies (optional - remove if you want to keep existing data)
        # Organization.objects.filter(name__in=self.get_insurance_companies()).delete()
        
        insurance_companies = self.get_insurance_companies()
        
        created_count = 0
        updated_count = 0
        
        for company_name in insurance_companies:
            org, created = Organization.objects.get_or_create(
                name=company_name,
                defaults={
                    'slug': company_name.lower().replace(' ', '-').replace(',', '').replace('.', ''),
                    'description': f'{company_name} - Insurance Company',
                    'user_limit': 100,
                    'subscription_tier': 'PRO',
                    'approval_workflow': 'AUTO_APPROVE',
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {company_name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Updated: {company_name}'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: {created_count} created, {updated_count} updated insurance companies'
            )
        )
    
    def get_insurance_companies(self):
        """List of insurance companies to populate"""
        return [
            # Leading Insurance Companies
            'Britam Holdings',
            'CIC Insurance Group',
            'Jubilee Insurance Company Limited',
            'ICEA LION Group',
            'Old Mutual Holdings (formerly UAP)',
            'APA Insurance Limited',
            'Sanlam Kenya PLC',
            'GA Insurance Limited',
            'Heritage Insurance Company',
            'Madison Insurance Company Limited',
            
            # Other Registered Insurers
            'AAR Insurance Kenya',
            'Absa Life Assurance Kenya',
            'Africa Merchant Assurance Company (AMACO)',
            'Cannon Assurance Limited',
            'Corporate Insurance Company Limited',
            'Directline Assurance Company',
            'Equity Life Assurance',
            'Fidelity Shield Insurance Company',
            'First Assurance Kenya Limited',
            'Geminia Insurance Company',
            'Intra Africa Assurance Company',
            'Invesco Assurance Company',
            'Kenindia Assurance Company',
            'Kenya Orient Insurance Limited',
            'Liberty Life Assurance Kenya',
            'Mayfair Insurance Company',
            'Occidental Insurance Company',
            'Pacis Insurance Company',
            'Pioneer Assurance Company',
            'Prudential Life Assurance',
            'Takaful Insurance of Africa',
            'Tausi Assurance Company',
            'The Monarch Insurance Company',
            'Trident Insurance Company',
            'Xplico Insurance Company'
        ]
