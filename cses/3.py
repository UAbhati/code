s = str(input())
n = len(s)
count = 0
max_count = 0
for i in range(1, n):
    if s[i] == s[i-1]:
        count += 1
        max_count = max(max_count, count)
    else:
        count = 0
print(max_count + 1)