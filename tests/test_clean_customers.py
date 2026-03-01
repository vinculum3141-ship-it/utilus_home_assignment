"""
Tests for customer data cleaning logic.
"""

import pandas as pd
import pytest

from src.transformers.clean_customers import CustomerDataCleaner, clean_customers_bronze_to_silver


class TestCustomerDataCleaner:
    """Test suite for CustomerDataCleaner class."""

    def test_clean_customer_id_strips_whitespace(self):
        """Test that customer_id whitespace is stripped."""
        df = pd.DataFrame({
            'customer_id': [' C001 ', 'C002  ', '  C003'],
            'signup_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'country': ['US', 'UK', 'CA']
        })
        cleaner = CustomerDataCleaner()
        result = cleaner._clean_customer_id(df)
        
        assert result['customer_id'].tolist() == ['C001', 'C002', 'C003']

    def test_clean_customer_id_removes_duplicates(self):
        """Test that duplicate customer_id entries are removed (keeps first)."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002', 'C002', 'C003'],
            'signup_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
            'country': ['US', 'UK', 'DE', 'CA']
        })
        cleaner = CustomerDataCleaner()
        result = cleaner._clean_customer_id(df)
        
        # Should keep only first occurrence of C002
        assert len(result) == 3
        assert result['customer_id'].tolist() == ['C001', 'C002', 'C003']
        assert result[result['customer_id'] == 'C002']['country'].iloc[0] == 'UK'
        # Note: C002 ID is NOT in removed_customer_ids because we keep the first occurrence
        # Only the duplicate row is removed, the customer still exists

    def test_clean_customer_id_handles_multiple_duplicates(self):
        """Test handling of customer_id with more than 2 occurrences."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C001', 'C001', 'C002'],
            'signup_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
            'country': ['US', 'UK', 'DE', 'CA']
        })
        cleaner = CustomerDataCleaner()
        result = cleaner._clean_customer_id(df)
        
        # Should keep only first occurrence
        assert len(result) == 2
        assert result['customer_id'].tolist() == ['C001', 'C002']
        assert result[result['customer_id'] == 'C001']['country'].iloc[0] == 'US'

    def test_clean_signup_date_strips_whitespace(self):
        """Test that signup_date whitespace is stripped."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002', 'C003'],
            'signup_date': [' 2024-01-01 ', '2024-01-02  ', '  2024-01-03'],
            'country': ['US', 'UK', 'CA']
        })
        cleaner = CustomerDataCleaner()
        result = cleaner._clean_signup_date(df)
        
        # Verify dates are valid (will be datetime64 after parsing)
        assert len(result) == 3
        assert str(result['signup_date'].dtype).startswith('datetime64')

    def test_clean_signup_date_removes_empty_dates(self):
        """Test that empty signup_date rows are removed."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002', 'C003'],
            'signup_date': ['2024-01-01', '', '2024-01-03'],
            'country': ['US', 'UK', 'CA']
        })
        cleaner = CustomerDataCleaner()
        result = cleaner._clean_signup_date(df)
        
        assert len(result) == 2
        assert 'C002' not in result['customer_id'].values
        assert 'C002' in cleaner.removed_customer_ids

    def test_clean_signup_date_removes_malformed_dates(self):
        """Test that malformed signup_date values are removed."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002', 'C003', 'C004'],
            'signup_date': ['2024-01-01', '2024-13-05', '2024-02-30', '2024-01-04'],
            'country': ['US', 'UK', 'DE', 'CA']
        })
        cleaner = CustomerDataCleaner()
        result = cleaner._clean_signup_date(df)
        
        # C002 has month 13, C003 has February 30th - both invalid
        assert len(result) == 2
        assert result['customer_id'].tolist() == ['C001', 'C004']
        assert 'C002' in cleaner.removed_customer_ids
        assert 'C003' in cleaner.removed_customer_ids

    def test_clean_country_strips_whitespace(self):
        """Test that country whitespace is stripped and values are uppercased."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002', 'C003'],
            'signup_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'country': [' us ', 'Uk  ', '  cA']
        })
        cleaner = CustomerDataCleaner()
        result = cleaner._clean_country(df)
        
        assert result['country'].tolist() == ['US', 'UK', 'CA']

    def test_clean_country_handles_missing_values(self):
        """Test that missing country values are logged but kept."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002', 'C003'],
            'signup_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'country': ['US', '', 'CA']
        })
        cleaner = CustomerDataCleaner()
        result = cleaner._clean_country(df)
        
        # Should keep all rows, empty country is allowed
        assert len(result) == 3
        assert result['customer_id'].tolist() == ['C001', 'C002', 'C003']

    def test_clean_full_pipeline(self):
        """Test the complete cleaning pipeline."""
        df = pd.DataFrame({
            'customer_id': [' C001 ', 'C002', 'C002', 'C003', 'C004'],
            'signup_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-13-05', '2024-01-05'],
            'country': ['US', 'UK', 'DE', 'CA', '']
        })
        cleaner = CustomerDataCleaner()
        result = cleaner.clean(df)
        
        # C002 duplicate removed (row, not ID), C003 malformed date removed
        assert len(result) == 3
        assert result['customer_id'].tolist() == ['C001', 'C002', 'C004']
        # Only C003 is in removed_customer_ids (malformed date)
        # C002 is NOT removed because we keep the first occurrence
        assert 'C003' in cleaner.removed_customer_ids
        assert 'C002' not in cleaner.removed_customer_ids

    def test_removed_customer_ids_tracking(self):
        """Test that removed_customer_ids correctly tracks all removals."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002', 'C002', 'C003', 'C004'],
            'signup_date': ['2024-01-01', '2024-01-02', '2024-01-03', '', '2024-13-05'],
            'country': ['US', 'UK', 'DE', 'CA', 'FR']
        })
        cleaner = CustomerDataCleaner()
        result = cleaner.clean(df)
        
        # Should track: C003 (empty date), C004 (malformed date)
        # C002 is NOT tracked because we keep the first occurrence (customer still exists)
        assert len(cleaner.removed_customer_ids) == 2
        assert 'C003' in cleaner.removed_customer_ids
        assert 'C004' in cleaner.removed_customer_ids
        assert 'C002' not in cleaner.removed_customer_ids
        assert len(result) == 2  # Only C001 and first C002 remain


class TestBronzeToSilverIntegration:
    """Integration tests for bronze to silver cleaning."""

    def test_clean_customers_bronze_to_silver(self, tmp_path):
        """Test the full bronze to silver cleaning process."""
        # Create bronze CSV
        bronze_path = tmp_path / "customers_bronze.csv"
        bronze_df = pd.DataFrame({
            'customer_id': ['C001', 'C002', 'C002', 'C003'],
            'signup_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-13-05'],
            'country': ['US', 'UK', 'DE', 'CA']
        })
        bronze_df.to_csv(bronze_path, index=False)
        
        silver_path = tmp_path / "customers_silver.csv"
        
        # Run cleaning
        removed_ids = clean_customers_bronze_to_silver(
            bronze_path=bronze_path,
            silver_path=silver_path
        )
        
        # Verify results
        assert silver_path.exists()
        silver_df = pd.read_csv(silver_path)
        assert len(silver_df) == 2  # C001 and first C002
        # Only C003 removed (malformed date), C002 kept (first occurrence)
        assert 'C003' in removed_ids
        assert 'C002' not in removed_ids
        assert len(removed_ids) == 1
