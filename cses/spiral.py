t = int(input())
for i in range(t):
    y, x = map(int, input().split())
    n = max(y, x)
    if n % 2 == 0:
        if y == n:
            print(n**2 - x + 1)
        else:
            print((n-1)**2 + y)
    else:
        if x == n:
            print(n**2 - y + 1)
        else:
            print((n-1)**2 + x)