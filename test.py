n=16
count = 0
for i in range(n+1):
    k=1
    while k< i:
        count+=1
        k=k*2

print(count)