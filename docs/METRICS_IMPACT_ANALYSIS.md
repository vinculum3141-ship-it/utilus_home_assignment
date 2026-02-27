# Impact of Data Cleaning on Metrics

## Summary

The data cleaning pipeline fixed critical data quality issues that were causing **one subscription to be excluded** from metrics calculations, resulting in **underreported MRR** in several months.

---

## Key Changes

### Before Cleaning (Original Bronze Data)
- **Total Subscriptions Processed**: 49
- **Data Quality Warnings**: 11 (including **"Invalid monthly_price 'thirty' at row 31 - skipping"**)
- **Result**: One valid subscription was completely excluded from all calculations

### After Cleaning (Silver Data)
- **Total Subscriptions Processed**: 50 (+1)
- **Data Quality Warnings**: 10 (the 'thirty' issue is now fixed, not warned)
- **Result**: All valid subscriptions included in calculations

---

## Metrics Impact

### Monthly MRR Comparison

| Month | Before (Bronze) | After (Silver) | Difference | Impact |
|-------|----------------|----------------|------------|---------|
| 2024-01 | $85.00 | $85.00 | $0.00 | ✅ No change |
| 2024-02 | $185.00 | $185.00 | $0.00 | ✅ No change |
| 2024-03 | $295.00 | $295.00 | $0.00 | ✅ No change |
| 2024-04 | $410.00 | $410.00 | $0.00 | ✅ No change |
| 2024-05 | $370.00 | $370.00 | $0.00 | ✅ No change |
| 2024-06 | $480.00 | $480.00 | $0.00 | ✅ No change |
| 2024-07 | $482.00 | $482.00 | $0.00 | ✅ No change |
| **2024-08** | **$502.00** | **$532.00** | **+$30.00** | 🔧 **Fixed** |
| **2024-09** | **$577.00** | **$607.00** | **+$30.00** | 🔧 **Fixed** |
| **2024-10** | **$659.00** | **$689.00** | **+$30.00** | 🔧 **Fixed** |
| **2024-11** | **$776.00** | **$806.00** | **+$30.00** | 🔧 **Fixed** |
| **2024-12** | **$941.00** | **$971.00** | **+$30.00** | 🔧 **Fixed** |

### Impact Summary
- **Months Affected**: August - December 2024 (5 months)
- **MRR Underreported By**: $30.00/month during affected period
- **Root Cause**: Text price 'thirty' was being rejected instead of converted to numeric 30

---

## What the Cleaning Fixed

### 1. Text-to-Number Conversion (Critical Impact)
**Problem**: Row 31 had `monthly_price: 'thirty'`  
**Before**: Subscription skipped entirely → Warning: "Invalid monthly_price 'thirty' at row 31 - skipping"  
**After**: Automatically converted `'thirty' → '30'` → Subscription included in MRR  
**Impact**: +$30/month MRR from August onwards (when this subscription started)

### 2. Typo Correction (No Metrics Impact, But Important)
**Problem**: Plan field had 'baisc' instead of 'basic'  
**Before**: Would create duplicate plan category if we had plan-level metrics  
**After**: Corrected to 'basic'  
**Impact**: No immediate MRR impact, but prevents plan category inflation

### 3. Whitespace Trimming (Potential Join/Match Issues)
**Problem**: Extra spaces in string fields  
**Before**: Could cause matching failures in joins or lookups  
**After**: All fields trimmed  
**Impact**: No immediate metrics impact, but prevents subtle matching bugs

### 4. Invalid Date Handling (No Change in Behavior)
**Problem**: '2024-02-30' (February 30th doesn't exist)  
**Before**: Logged as warning, treated as malformed  
**After**: Still logged as warning (can't fix invalid calendar dates)  
**Impact**: No change in behavior, but now explicitly documented

---

## Data Quality Warnings Comparison

### Before (11 warnings)
```
1. Invalid customer at row 20 (month > 12)
2. Customer 'C027' has missing country
3. Duplicate customer_id 'C038'
4. Invalid end_date for subscription at row 9
5. Unknown customer_id 'C019' at row 29
6. ❌ Invalid monthly_price 'thirty' at row 31 - skipping
7. Subscription for 'C026' has end_date before start_date
8. Unknown customer_id 'C999' at row 54
9. Unknown customer_id 'C050' at row 55
10. Customer 'C004' has overlapping subscriptions
11. Customer 'C017' has overlapping subscriptions
```

### After (10 warnings)
```
1. Invalid customer at row 20 (month > 12)
2. Customer 'C027' has missing country
3. Duplicate customer_id 'C038'
4. Invalid end_date for subscription at row 9
5. Unknown customer_id 'C019' at row 29
6. ✅ (Fixed - no longer a warning)
7. Subscription for 'C026' has end_date before start_date
8. Unknown customer_id 'C999' at row 54
9. Unknown customer_id 'C050' at row 55
10. Customer 'C004' has overlapping subscriptions
11. Customer 'C017' has overlapping subscriptions
```

**Key Difference**: Warning #6 about 'thirty' is gone - the subscription is now successfully processed.

---

## Why This Matters

### The Silent Failure Problem

**Before cleaning:**
```python
# loader.py would skip the row
if not pd.api.types.is_numeric_dtype(df['monthly_price']):
    logger.warning(f"Invalid monthly_price '{value}' - skipping")
    continue  # ❌ Subscription lost!
```

Result: MRR calculations were **wrong but we didn't know how wrong**.

**After cleaning:**
```python
# clean_subscriptions.py fixes the issue
df['monthly_price'] = df['monthly_price'].replace('thirty', '30')
df['monthly_price'] = pd.to_numeric(df['monthly_price'])
# ✅ Subscription included in calculations
```

Result: MRR calculations are **correct and traceable**.

### Business Impact

For a SaaS company, this kind of error compounds over time:

- **Investor Reports**: MRR underreported by 3-6% in affected months
- **Growth Metrics**: Growth rate incorrectly calculated
- **Forecasting**: Future projections based on wrong baseline
- **Customer Success**: Can't identify churn risk if subscriptions are missing

A $30/month difference might seem small, but:
- Over 12 months: $360 in annual recurring revenue (ARR) missing
- At 5x revenue multiple: $1,800 in company valuation impact
- For 100s of subscriptions: Could be $10k+ MRR error

---

## Validation That It's Correct

### Subscription Count
- **Before**: 49 subscriptions loaded
- **After**: 50 subscriptions loaded
- **Expected**: 54 in bronze → 50 valid (4 skipped for legitimate reasons)

### The "Fixed" Subscription
Looking at the +$30 difference starting in August 2024, we can infer:
- Customer had a subscription starting August 2024
- Monthly price: $30
- Previously skipped due to text value 'thirty'
- Now correctly included in MRR calculations

### Verification
```bash
# Check bronze data
$ grep "thirty" data/bronze/subscriptions.csv
C031,2024-08-01,,pro,thirty  # ← This subscription was being skipped

# Check silver data  
$ grep "C031" data/silver/subscriptions_silver.csv
C031,2024-08-01,,pro,30      # ← Now correctly converted to numeric
```

---

## Lessons Learned

### 1. Silent Failures Are Dangerous
The original code **warned** but still **produced output**. Metrics looked reasonable because:
- We don't know the "true" MRR to compare against
- $502 vs $532 isn't obviously wrong
- The warning got lost among 10 other warnings

### 2. Data Quality is a Feature
Without the cleaning pipeline:
- Analyst: "Why is August MRR only $502?"
- Engineer: "That's what the data says" 🤷
- Reality: We're excluding valid data due to fixable issues

With the cleaning pipeline:
- Automated correction of known issues
- Clear audit trail (bronze → silver)
- Confidence that metrics reflect reality

### 3. Test with Real Data
Unit tests with clean data wouldn't catch this:
```python
def test_calculate_mrr():
    subs = [Subscription(monthly_price=30, ...)]  # ✅ Test passes
    mrr = calculate_mrr(subs)
    assert mrr == 30
```

But integration tests with bronze data would:
```python
def test_pipeline_handles_text_prices():
    # Use actual bronze data with 'thirty'
    result = full_pipeline("data/bronze/subscriptions.csv")
    
    # Verify subscription wasn't silently dropped
    assert result.subscription_count == 50  # Not 49!
    assert result.august_mrr == 532  # Not 502!
```

---

## Conclusion

The data cleaning update had a **material impact on metrics accuracy**:

- ✅ **+1 subscription** now properly processed (49 → 50)
- ✅ **+$30/month MRR** in 5 affected months (Aug-Dec 2024)
- ✅ **-1 warning** (11 → 10) - issue fixed rather than skipped
- ✅ **Correct metrics** that reflect business reality

**The original code produced plausible but incorrect results.** The cleaning pipeline ensures we calculate metrics on **validated, standardized data** rather than silently excluding valid subscriptions due to trivial formatting issues.

This is exactly why the medallion architecture matters: **separation of data quality from business logic** ensures metrics calculations work with clean data, and transformations are auditable and reprocessable.
