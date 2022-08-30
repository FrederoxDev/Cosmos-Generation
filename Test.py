import threading

def function1(results, index):
    for x in range(10000):
        print("ONE")

    results[index] = "ONE"


def function2(results, index):
    for x in range(10000):
        print("TWO")

    results[index] = "TWO"


results = [None] * 2
 
t1 = threading.Thread(target=function1, args=(results, 0))
t2 = threading.Thread(target=function2, args=(results, 1))

t1.start()
t2.start()

t1.join()
t2.join()

print("Done")
print(results)