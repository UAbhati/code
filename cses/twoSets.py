n = int(input())
sum = 0
for i in range(1, n+1):
    sum += i
if(sum % 2 == 0):
    print("YES")
    ans = sum/2
    a = []
    b = []
    for j in range(n, 0,-1):
        if(j <= ans):
            a.append(j)
            ans -= j
        else:
            b.append(j)
    print(len(a))
    for j in a:
        print(j, end=" ")
    print()
    print(len(b))
    for j in b:
        print(j, end=" ")
else:
    print("NO")