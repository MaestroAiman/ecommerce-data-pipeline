"""
Data Processing Pipeline
Download data from S3, clean it, transform it, and upload results back to S3.
"""

import os
import boto3
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import tempfile

def process_ecommerce_data():
    """Download, process, and upload e-commerce data"""
    
    print("Starting data processing...")
    
    # Load environment variables
    load_dotenv()
    bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    if not bucket_name:
        print("ERROR: AWS_S3_BUCKET_NAME not found in .env file!")
        return False
    
    print(f"Processing data from bucket: {bucket_name}")
    
    try:
        # Create S3 client
        s3 = boto3.client('s3',region_name=region)
        
        # Step 1: Download data from S3
        print("\nStep 1: Downloading data from S3...")
        datasets = download_data_from_s3(s3, bucket_name)
        
        # Step 2: Clean and transform data
        print("\nStep 2: Cleaning and transforming data...")
        processed_datasets = transform_data(datasets)
        
        # Step 3: Create business metrics
        print("\nStep 3: Creating business metrics...")
        business_metrics = create_business_metrics(processed_datasets)
        
        # Step 4: Upload processed data back to S3
        print("\nStep 4: Uploading processed data to S3...")
        upload_success = upload_processed_data(s3, bucket_name, processed_datasets, business_metrics)
        
        if upload_success:
            print("\nSUCCESS: Data processing pipeline completed!")
            return True
        else:
            print("\nERROR: Failed to upload processed data")
            return False
            
    except Exception as e:
        print(f"ERROR: Data processing failed: {e}")
        return False

def download_data_from_s3(s3,bucket_name):

    datasets ={}

    data_files = ['customers.csv','products.csv','orders.csv','order_items.csv','reviews.csv']

    for file_name in data_files:
        try:
            print(f'Downloading {file_name}...')

            s3_key = f"raw-data/{file_name}"
            local_path = os.path.join(tempfile.gettempdir(),file_name)

            s3.download_file(bucket_name,s3_key,local_path)

            df = pd.read_csv(local_path)
            dataset_name = file_name.replace(".csv","")

            datasets[dataset_name] = df

            print(f'Loaded {dataset_name}: {len(df)} records')

            os.remove(local_path)
        
        except Exception as e:
            print(f"Failed to download {file_name}: {e}")

    return datasets


def clean_customers(customers):
    """Normalize emails, parse dates, derive age and age_group. Pure function."""
    customers = customers.copy()

    customers['email'] = customers['email'].str.lower().str.strip()

    customers['date_of_birth'] = pd.to_datetime(customers['date_of_birth'])
    customers['registration_date'] = pd.to_datetime(customers['registration_date'])

    customers['age'] = (datetime.now() - customers['date_of_birth']).dt.days // 365

    customers['age_group'] = pd.cut(customers['age'], bins=[0, 25, 35, 50, 65, 100],
                                     labels=['18-25', '26-35', '36-50', '51-65', '65+'])

    return customers

def clean_products(products):
    """Normalize product names, coerce price to numeric, derive price_category. Pure function."""
    products = products.copy()

    products['product_name'] = products['product_name'].str.strip()

    products['price'] = pd.to_numeric(products['price'], errors='coerce')

    products['price_category'] = pd.cut(products['price'], bins=[0, 50, 150, 500, float('inf')],
                                         labels=['Budget', 'Mid-range', 'Premium', 'Luxury'])

    return products

def clean_orders(orders):
    """Parse order_date, coerce total_amount to numeric, derive order_month/order_year. Pure function."""
    orders = orders.copy()

    orders['order_date'] = pd.to_datetime(orders['order_date'])

    orders['total_amount'] = pd.to_numeric(orders['total_amount'], errors='coerce')

    orders['order_month'] = orders['order_date'].dt.month
    orders['order_year'] = orders['order_date'].dt.year

    return orders

def clean_order_items(order_items):
    """Coerce quantity/unit_price to numeric and compute total_price. Pure function."""
    order_items = order_items.copy()

    order_items['quantity'] = pd.to_numeric(order_items['quantity'], errors='coerce')
    order_items['unit_price'] = pd.to_numeric(order_items['unit_price'], errors='coerce')

    order_items['total_price'] = order_items['quantity'] * order_items['unit_price']

    return order_items

def clean_reviews(reviews):
    """Parse review_date, coerce rating to numeric, derive rating_category. Pure function."""
    reviews = reviews.copy()

    reviews['review_date'] = pd.to_datetime(reviews['review_date'])

    reviews['rating'] = pd.to_numeric(reviews['rating'], errors='coerce')

    reviews['rating_category'] = reviews['rating'].apply(
        lambda x: 'Excellent' if x >= 4.5 else
                    'Good' if x >= 3.5 else
                    'Average' if x >= 2.5 else 'Poor'
    )

    return reviews

def compute_customer_metrics(customers_clean, orders_clean):
    """Customer lifetime value: spend/order-count/averages per customer, with age_group. Pure function."""
    customer_metrics = orders_clean.groupby('customer_id').agg({
        'total_amount': ['sum', 'count', 'mean'],
        'order_date': ['min', 'max']
    }).round(2)

    customer_metrics.columns = ['total_spent', 'order_count', 'ave_order_value', 'first_order', 'last_order']

    customer_metrics = customer_metrics.reset_index()

    customer_metrics = customer_metrics.merge(customers_clean[['customer_id', 'age_group']])

    return customer_metrics

def compute_product_metrics(products_clean, order_items_clean):
    """Product sales performance: quantity sold/revenue/order count per product. Pure function."""
    product_metrics = order_items_clean.groupby('product_id').agg({
        'quantity': 'sum',
        'total_price': 'sum',
        'order_id': 'count'
    }).round(2)

    product_metrics.columns = ['total_quantity_sold', 'total_revenue', 'number_of_orders']
    product_metrics = product_metrics.reset_index()

    product_metrics = product_metrics.merge(
        products_clean[['product_id', 'product_name', 'category', 'price']], on='product_id'
    )

    return product_metrics

def compute_monthly_sales(orders_clean):
    """Monthly revenue/order-count trend. Pure function."""
    monthly_sales = orders_clean.groupby(['order_year', 'order_month']).agg({
        'total_amount': 'sum',
        'order_id': 'count'
    }).round(2)

    monthly_sales.columns = ['total_revenue', 'order_count']
    monthly_sales = monthly_sales.reset_index()

    return monthly_sales

def transform_data(datasets):

    processed = {}

    if 'customers' in datasets:
        processed['customers_clean'] = clean_customers(datasets['customers'])
        print(f"Processed customers: {len(processed['customers_clean'])} records")

    if 'products' in datasets:
        processed['products_clean'] = clean_products(datasets['products'])
        print(f"Processed products: {len(processed['products_clean'])} records")

    if 'orders' in datasets:
        processed['orders_clean'] = clean_orders(datasets['orders'])
        print(f"Processed orders: {len(processed['orders_clean'])} records")

    if 'order_items' in datasets:
        processed['order_items_clean'] = clean_order_items(datasets['order_items'])
        print(f"Processed order_items: {len(processed['order_items_clean'])} records")

    if 'reviews' in datasets:
        processed['reviews_clean'] = clean_reviews(datasets['reviews'])
        print(f"Processed reviews: {len(processed['reviews_clean'])} records")

    return processed

def create_business_metrics(processed_datasets):

    metrics = {}

    if 'customers_clean' in processed_datasets and 'orders_clean' in processed_datasets:
        metrics['customer_metrics'] = compute_customer_metrics(
            processed_datasets['customers_clean'], processed_datasets['orders_clean']
        )
        print(f"Created customer metrics: {len(metrics['customer_metrics'])} customers")

    if 'products_clean' in processed_datasets and 'order_items_clean' in processed_datasets:
        metrics['product_metrics'] = compute_product_metrics(
            processed_datasets['products_clean'], processed_datasets['order_items_clean']
        )
        print(f"Created product metrics: {len(metrics['product_metrics'])} products")

    if 'orders_clean' in processed_datasets:
        metrics['monthly_sales'] = compute_monthly_sales(processed_datasets['orders_clean'])
        print(f"Created monthly sales trends: {len(metrics['monthly_sales'])} months")

    return metrics

def to_athena_parquet(df):
    """Return a copy of df made safe for Athena-compatible Parquet: no pandas
    category/Period dtypes (cast to str), caller still needs coerce_timestamps="ms"
    at write time for nanosecond timestamps."""
    df = df.copy()
    for col in df.columns:
        if isinstance(df[col].dtype, pd.CategoricalDtype):
            df[col] = df[col].astype(str)
    return df

def upload_processed_data(s3,bucket_name,processed,metrics):

    upload_count = 0
    total_files = len(processed) + len(metrics)

    # Upload processed datasets
    for dataset_name, df in processed.items():
        try:
            # Save a temporary parquet file (S3 key is fixed, so a rerun
            # overwrites it in place - no duplicate/partitioned files)
            local_path = os.path.join(tempfile.gettempdir(), f"{dataset_name}.parquet")
            to_athena_parquet(df).to_parquet(
                local_path, engine="pyarrow", index=False,
                coerce_timestamps="ms", allow_truncated_timestamps=True
            )

            # Upload to S3
            s3_key = f"processed/{dataset_name}.parquet"
            s3.upload_file(local_path,bucket_name,s3_key)

            print(f"Uploaded {dataset_name}: {len(df)} records")
            upload_count += 1

            # Clean up
            os.remove(local_path)

        except Exception as e:
            print(f"Failed to upload {dataset_name}: {e}")

        # Upload business metrics
    for metric_name, df in metrics.items():
        try:
            # Save a temporary parquet file
            local_path = os.path.join(tempfile.gettempdir(), f"{metric_name}.parquet")
            to_athena_parquet(df).to_parquet(
                local_path, engine="pyarrow", index=False,
                coerce_timestamps="ms", allow_truncated_timestamps=True
            )

            # Upload to S3 - each metric gets its own folder/prefix so it can be
            # mapped to its own Athena table (see sql/create_tables.sql)
            s3_key = f"processed/metrics/{metric_name}/{metric_name}.parquet"
            s3.upload_file(local_path,bucket_name,s3_key)

            print(f"Uploaded {metric_name}: {len(df)} records")
            upload_count += 1

            # Clean up
            os.remove(local_path)

        except Exception as e:
            print(f"Failed to upload {metric_name}: {e}")

    return upload_count == total_files



if __name__ == "__main__":

    success = process_ecommerce_data()

    if success:
        print("\nNext step: Orchestration with Prefect!")

    else:
        print("\nFix the errors and try again")
