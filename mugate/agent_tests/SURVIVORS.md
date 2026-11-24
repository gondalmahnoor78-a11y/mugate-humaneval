# Surviving gate mutants shown to the agent (feedback round 1)
Each entry is a first-order mutant of the candidate program that the agent's current (vanilla) suite does NOT detect. Lines prefixed '-' are original code, '+' the mutated code. Held-out mutants are never listed here.

## HumanEval/35 (`max_element`) - 1 surviving gate mutant(s)

m004 [ROR]
```diff
-        if e > m:
+        if e >= m:
```

## HumanEval/39 (`prime_fib`) - 1 surviving gate mutant(s)

m034 [AOR]
```diff
-        for k in range(2, min(int(math.sqrt(p)) + 1, p - 1)):
+        for k in range(2, min(int(math.sqrt(p)) + 1, p + 1)):
```

## HumanEval/40 (`triples_sum_to_zero`) - 2 surviving gate mutant(s)

m002 [AOR]
```diff
-        for j in range(i + 1, len(l)):
+        for j in range(i - 1, len(l)):
```

m005 [AOR]
```diff
-            for k in range(j + 1, len(l)):
+            for k in range(j - 1, len(l)):
```

## HumanEval/59 (`largest_prime_factor`) - 1 surviving gate mutant(s)

m012 [AOR]
```diff
-    for j in range(2, n + 1):
+    for j in range(2, n - 1):
```

## HumanEval/71 (`triangle_area`) - 2 surviving gate mutant(s)

m011 [ROR]
```diff
-    if a + b <= c or a + c <= b or b + c <= a:
+    if a + b <= c or a + c < b or b + c <= a:
```

m013 [ROR]
```diff
-    if a + b <= c or a + c <= b or b + c <= a:
+    if a + b <= c or a + c <= b or b + c < a:
```

## HumanEval/108 (`count_nums`) - 2 surviving gate mutant(s)

m007 [ROR]
```diff
-        if n < 0:
+        if n <= 0:
```

m011 [AOR]
```diff
-        n[0] = n[0] * neg
+        n[0] = n[0] / neg
```

## HumanEval/114 (`minSubArraySum`) - 1 surviving gate mutant(s)

m016 [ROR]
```diff
-        if s < 0:
+        if s <= 0:
```

## HumanEval/129 (`minPath`) - 5 surviving gate mutant(s)

m004 [AOR]
```diff
-    val = n * n + 1
+    val = n * n - 1
```

m005 [AOR]
```diff
-    val = n * n + 1
+    val = n / n + 1
```

m021 [ROR]
```diff
-                if i != 0:
+                if i == 0:
```

m022 [CND]
```diff
-                if i != 0:
+                if not i != 0:
```

m052 [AOR]
```diff
-                    temp.append(grid[i + 1][j])
+                    temp.append(grid[i - 1][j])
```

## HumanEval/135 (`can_arrange`) - 1 surviving gate mutant(s)

m013 [ROR]
```diff
-        if arr[i] < arr[i - 1]:
+        if arr[i] <= arr[i - 1]:
```

## HumanEval/148 (`bf`) - 1 surviving gate mutant(s)

m006 [ROR]
```diff
-    if planet1_index < planet2_index:
+    if planet1_index <= planet2_index:
```

## HumanEval/151 (`double_the_difference`) - 1 surviving gate mutant(s)

m006 [ROR]
```diff
-    return sum([i ** 2 for i in lst if i > 0 and i % 2 != 0 and ('.' not in str(i))])
+    return sum([i ** 2 for i in lst if i >= 0 and i % 2 != 0 and ('.' not in str(i))])
```
