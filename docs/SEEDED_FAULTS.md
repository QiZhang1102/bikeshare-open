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
