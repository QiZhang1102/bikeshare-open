# Seeded faults

Failures captured before the corresponding fix lands, so the red state stays
on record next to the test that produces it.

## Exercise 1: cnt_roll_3 before implementation

Command:

```bash
python -m pytest -q tests/test_leakage.py::test_cnt_roll_3_is_mean_of_three_prior_days
```

Actual failure:

```
F                                                                        [100%]
=================================== FAILURES ===================================
_________________ test_cnt_roll_3_is_mean_of_three_prior_days __________________

feats =         dteday  instant  season  ...  cnt_lag_1 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      822.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1796.0     920.0  1531.428571

[714 rows x 28 columns]

    def test_cnt_roll_3_is_mean_of_three_prior_days(feats):
        """cnt_roll_3 for date d must be the mean of cnt on the three days before it."""
        by_date = (
            load_raw().sort_values("dteday").reset_index(drop=True).set_index("dteday")[TARGET]
        )
        date = pd.Timestamp("2011-01-12")
        window = [date - pd.Timedelta(days=k) for k in range(1, 4)]
        counts = [by_date[d] for d in window]
        expected = sum(counts) / len(counts)
        print(f"raw cnt Jan 9/10/11, 2011: {list(counts)}  mean: {expected}")
>       actual = feats.set_index("dteday").cnt_roll_3[date]
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_leakage.py:79: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self =             instant  season      yr  ... cnt_lag_1 cnt_lag_7   cnt_roll_7
dteday                               ...    ... 1787.0  1530.142857
2012-12-31    731.0  WINTER  2012.0  ...    1796.0     920.0  1531.428571

[714 rows x 27 columns]
name = 'cnt_roll_3'

    @final
    def __getattr__(self, name: str):
        """
        After regular attribute access, try looking up the name
        This allows simpler access to columns for interactive use.
        """
        # Note: obj.x will always call obj.__getattribute__('x') prior to
        # calling obj.__getattr__('x').
        if (
            name not in self._internal_names_set
            and name not in self._metadata
            and name not in self._accessors
            and self._info_axis._can_hold_identifiers_and_holds_name(name)
        ):
            return self[name]
>       return object.__getattribute__(self, name)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: 'DataFrame' object has no attribute 'cnt_roll_3'. Did you mean: 'cnt_roll_7'?

.venv/lib/python3.12/site-packages/pandas/core/generic.py:6194: AttributeError
----------------------------- Captured stdout call -----------------------------
raw cnt Jan 9/10/11, 2011: [np.int64(1263), np.int64(1321), np.int64(822)]  mean: 1135.3333333333333
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_cnt_roll_3_is_mean_of_three_prior_days - A...
1 failed in 0.68s
```

## Exercise 2 — Haoshuo Bi

The following experiments were originally conducted on Haoshuo Bi's independent implementation using cnt_roll_std_7. The group implementation uses Mia's cnt_roll_3 instead. Historical experimental outputs are preserved without modification.

Original Exercise 2 commits: d8d891c, 9e69478, 2f30e81, 2c4276f, 8279be4, 613815f.

## Unclassified raw column verification

Injected an unknown column into an in-memory copy of the raw data.
The original CSV was not modified.

```text
PASS: Unknown column correctly detected.
Actual assertion error: Unclassified raw columns: ['secret_target']

```

## Exercise 2 — Fault 1: Forbidden column leakage

Injected an exception in feature_columns() to allow casual into the model.

### Exact change

```diff
diff --git a/src/features.py b/src/features.py
index f25e5f5..2435f3c 100644
--- a/src/features.py
+++ b/src/features.py
@@ -82,7 +82,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN or c == "casual"]
 
 
 if __name__ == "__main__":

```

### Automatic hook result

The PostToolUse hook fired automatically after the Edit tool call.

```text
AssertionError: forbidden columns in feature set: {'casual'}
1 failed, 7 passed in 12.48s
```

### Full failing test output

```text
python -m pytest tests/ -q
......F.........                                                         [100%]
=================================== FAILURES ===================================
__________________________ test_no_forbidden_features __________________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7 cnt_roll_std_7
0   2011-01-10     10.0  WINTER  ...     1...857     886.694316
713 2012-12-31    731.0  WINTER  ...      920.0  1531.428571     887.135250

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'cnt_roll_std_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 15 passed in 28.88s
make: *** [Makefile:16: test] Error 1

```

### Hook stderr (manual reproduction)

```text
Leakage tests failed after editing src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7 cnt_roll_std_7
0   2011-01-10     10.0  WINTER  ...     1...857     886.694316
713 2012-12-31    731.0  WINTER  ...      920.0  1531.428571     887.135250

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'cnt_roll_std_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 7 passed in 11.21s

```

### Repair

Claude restored the original forbidden-column filter in one repair turn. No tests were changed.

```text
python -m pytest tests/ -q
................                                                         [100%]
16 passed in 16.83s

```

## Exercise 2 — Fault 2: Rolling mean target leakage

Removed shift(1) from cnt_roll_7, incorrectly including the current-day target.

### Exact change

```diff
diff --git a/src/features.py b/src/features.py
index f25e5f5..efd6e50 100644
--- a/src/features.py
+++ b/src/features.py
@@ -73,7 +73,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # If you add a longer lag, raise LAG_WARMUP in src/config.py.
     out["cnt_lag_1"] = out[TARGET].shift(1)
     out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
     out["cnt_roll_std_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).std(ddof=1)
 
     return out.dropna().reset_index(drop=True)

```

### Automatic hook result

The PostToolUse hook automatically detected the incorrect rolling mean.

```text
Obtained: 4389.0
Expected: 4414.857142857143 ± 0.00441486
1 failed, 7 passed in 11.54s
```

### Full failing test output

```text
python -m pytest tests/ -q
.........F......                                                         [100%]
=================================== FAILURES ===================================
_______________________ test_rolling_mean_excludes_today _______________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7 cnt_roll_std_7
0   2011-01-10     10.0  WINTER  ...     1...571     886.694316
713 2012-12-31    731.0  WINTER  ...      920.0  1789.857143     887.135250

[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 15 passed in 28.55s
make: *** [Makefile:16: test] Error 1

```

### Hook stderr (manual reproduction)

```text
Leakage tests failed after editing src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 11.53s

```

### Repair

Claude restored shift(1) in one repair turn. The new standard deviation feature and all tests remained unchanged.

```text
python -m pytest tests/ -q
................                                                         [100%]
16 passed in 17.49s

```

## Exercise 2 — Fault 3: Unknown weather labels

Removed the ValueError guard from encode_weather(). Unknown labels silently mapped to NaN.

### Initial test blind spot

```text
python -m pytest tests/ -q
................                                                         [100%]
16 passed in 17.28s

```

### Added regression test and failure

```text
python -m pytest tests/ -q
.............F...                                                        [100%]
=================================== FAILURES ===================================
_________________________ test_unknown_weather_raises __________________________

    def test_unknown_weather_raises():
        """encode_weather should raise ValueError on unknown labels."""
        from src.features import encode_weather
    
>       with pytest.raises(ValueError, match="unmapped weather labels"):
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:96: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_unknown_weather_raises - Failed: DID NOT R...
1 failed, 16 passed in 30.09s
make: *** [Makefile:16: test] Error 1

```

### Automatic hook result after adding regression test

The fault was reintroduced using Edit. Actual hook output transcribed from Claude Code:

```text
PostToolUse:Edit hook reported a problem
FAILED tests/test_leakage.py::test_unknown_weather_raises - Failed: DID NOT RAISE ValueError
1 failed, 8 passed in 11.46s
```

### Repair

Two repair prompts were needed for the initial repair. The original guard was restored and the new regression test was retained.

```text
python -m pytest tests/ -q
.................                                                        [100%]
17 passed in 18.02s

```

The repeated fault injection was subsequently reverted using git restore in one additional turn.
An earlier manual hook attempt failed because Claude invoked a nonexistent Python module; it was not valid hook evidence.

## Exercise 2 — Fault 4: Raw data write protection

Attempted Bash command:

    touch data/raw/ma6_permission_probe.tmp

Actual permission output:

    Not run · permission denied · rule from shared project settings
    Reason: Permission to use Bash with command touch data/raw/ma6_permission_probe.tmp has been denied.

The permission system automatically denied the command without user intervention. No alternative write methods were attempted. No repair was needed (0 repair turns).

This demonstrates that the tested Bash write was blocked by the existing permission configuration.

## Fault 4 Supplement: Bash cp Permission Test

Date: November 25, 2026

Following Qi Zhang's peer audit, I repeated the fourth
fault using the actual Bash cp command required by the
assignment, rather than touch.

### Actual command attempted

```bash
cp /tmp/ma6_cp_permission_probe.tmp data/raw/ma6_cp_permission_probe.tmp 2>&1; echo "EXIT_CODE=$?"
```

The source was a harmless temporary file containing
"permission_test_probe". The original bike_daily.csv
was not targeted or overwritten.

### Actual permission output

```text
1 action not run · permission denied · rule from shared project settings
Reason: Permission to use Bash with command cp /tmp/ma6_cp_permission_probe.tmp data/raw/ma6_cp_permission_probe.tmp 2>&1; echo "EXIT_CODE=$?" has been denied.
```

### Result

- Permission response: DENIED by shared project settings.
- The command was blocked before shell execution.
- No shell exit code or shell stderr was produced.
- No PostToolUse hook execution was observed.
- Repair turns required: 0.
- No permission rules or hooks were changed.

### Independent verification

After exiting Claude Code, I ran:

```bash
sha256sum data/raw/bike_daily.csv
git status --short
ls -l data/raw/
```

Actual SHA256 output:

```text
a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc  data/raw/bike_daily.csv
```

The hash matched the original hash recorded before the
experiment. Git status produced no output, and the raw
data directory contained only bike_daily.csv.

### Enforcement and limitations

The PostToolUse leakage hook does not directly protect
against arbitrary Bash file-copy operations. In this
experiment, the existing project permission rules blocked
the cp command before execution.

A PreToolUse hook on Bash could provide additional
protection. Filesystem write restrictions or a raw-data
hash check could also detect or prevent unauthorized
changes.

This experiment confirms that the specific cp command
was blocked. It does not prove that every possible Bash
write operation would be blocked.

### Conclusion

The missing cp experiment identified during peer review
has now been completed. The original raw data remained
unchanged, and no model scores were affected by this
permission test.

Claude Code session:
55dcbac9-871a-4503-8e0b-9f0478967b68
