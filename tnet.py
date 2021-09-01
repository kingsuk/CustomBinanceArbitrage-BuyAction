n = 10
i = 1
sum = 0
a =1
b = 1
while i <= n :
    sum = a+b
    a=b
    b=sum
    i = i +1

print(sum)