import duckdb
import os
import pandas as pd

def run_suite():
    db_path = 'data/ecommerce_analytics.duckdb'
    con = duckdb.connect(db_path)
    
    sql_files = [
        ('01_data_quality_audit.sql', '1. Data Quality & Referential Integrity Audit'),
        ('02_overall_funnel.sql', '2. Overall Funnel Conversion & Drop-off Analysis'),
        ('03_search_performance.sql', '3. Search Relevance, Reformulation & CTR Analysis'),
        ('04_pdp_and_sizing.sql', '4. PDP Sizing Availability, Dwell Time & ATCR'),
        ('05_cart_checkout.sql', '5. Cart-to-Order Conversion & Shipping Fee Analysis'),
        ('06_platform_analysis.sql', '6. Platform Funnel Comparison (iOS vs Android vs Mobile Web vs Desktop)'),
        ('07_user_segmentation.sql', '7. User Cohort & Acquisition Channel Analysis'),
        ('08_category_analysis.sql', '8. Merchandise Category & 4-Quadrant Strategic Matrix'),
        ('09_period_comparison.sql', '9. Period Comparison (Period 1 vs Period 2)'),
        ('10_opportunity_analysis.sql', '10. Friction Area Sizing & Opportunity Analysis')
    ]
    
    report_lines = [
        '# E-commerce Product Analytics: SQL Analytical Suite Results',
        '',
        '**Database:** data/ecommerce_analytics.duckdb  ',
        '**Observation Window:** 56 Days (Period 1: Days 1–28, Period 2: Days 29–56)  ',
        '**Generated Volume:** 119,390 Events/Facts across 7 tables  ',
        '',
        '---',
        ''
    ]
    
    for filename, title in sql_files:
        filepath = os.path.join('sql', filename)
        print(f'Executing {filename}...')
        with open(filepath, 'r', encoding='utf-8') as f:
            sql_text = f.read()
            
        report_lines.append(f'## {title}')
        report_lines.append(f'*Source: sql/{filename}*')
        report_lines.append('')
        
        queries = [q.strip() for q in sql_text.split(';') if q.strip()]
        for idx, q in enumerate(queries):
            comment_header = []
            query_code = []
            for line in q.split('\n'):
                if line.strip().startswith('--') and not query_code:
                    comment_header.append(line.strip()[2:].strip())
                else:
                    query_code.append(line)
                    
            clean_query = '\n'.join(query_code).strip()
            if not clean_query:
                continue
                
            if comment_header:
                report_lines.append(f'**Query Focus:** {comment_header[0]}')
                report_lines.append('')
                
            try:
                res_df = con.execute(clean_query).df()
                # format numbers nicely
                for col in res_df.select_dtypes(include=['float']).columns:
                    res_df[col] = res_df[col].apply(lambda x: f'{x:.2f}' if pd.notnull(x) else '')
                md_table = res_df.to_markdown(index=False)
                report_lines.append(md_table)
                report_lines.append('')
            except Exception as e:
                report_lines.append(f'**Execution Error:** {e}')
                report_lines.append('')
                print(f'Error in {filename}: {e}')
                
        report_lines.append('---')
        report_lines.append('')
        
    con.close()
    
    os.makedirs('reports', exist_ok=True)
    report_path = 'reports/sql_analysis_results.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
        
    print(f'Successfully generated {report_path}')

if __name__ == '__main__':
    run_suite()
