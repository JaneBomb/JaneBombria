# Jane Bombria
# CS 2300
# PA4
# This program will read inputs from a file. With the input this program will create a matrix and manipulate the matrix per the directions.
import math
import numpy as np
import matplotlib.pyplot as plt

# FUNCTIONS
# will take in the address for a file. Will open the file and store the inputs in an array and send back to main
def readFile(file):
    with open(file, 'r') as openFile:
        list = []
        for line in openFile:
            for num in line.split():
                list.append(int(num))
    return list

# creates an empty matrix with the correct dimensions (n x 2) and fills the matrix with information from the file
# fills column first, the moves to next column
# returns the filled matrix for x
def createXMatrix(rowNum, colNum, values):
    mat = np.zeros((rowNum, colNum), dtype = int)
    for i, val in enumerate(values):
        rowIndex = i % rowNum
        colIndex = i // rowNum
        mat[rowIndex][colIndex] = val
    return mat

# creates an empty matrix with the correct dimensions (n x 1) and fills the matrix with information from the file
# fills column first, the moves to next column
# returns the filled matrix for y
def createYMatrix(rowNum, values):
    mat = np.zeros((rowNum, 1), dtype = int)
    for i, val in enumerate(values):
        rowIndex = i % rowNum
        colIndex = i // rowNum
        mat[rowIndex][colIndex] = val
    return mat

# takes in a matrix
# creates the transpose of the matrix
# returns transposed matrix
def transposeMat(mat):
    transpose = np.transpose(mat)
    return transpose

# takes in 2 matrices
# multiplies both matrices together
# returns the product matrix from the multiplication
def multiplyMatrices(matA, matB):
    result = np.matmul(matA,matB)
    return result


#------------MAIN-----------
# read file
fileName = 'exampleInput.txt'
file = readFile(fileName)

# store arr length for later use
arrLen = len(file)

# split x into own list
xArr = []
xArrNo1 = []
xLen = 0

for i in file[0: arrLen-1: 2]:
    xArrNo1.append(i)
    xArr.append(i)
    xLen += 1
# adding 1s to front of array to fill first column with 1s in matrix
for i in range (xLen):
    xArr.insert(0, 1)

# split y into own list
yArr = []
yLen = 0
for i in file[1: arrLen: 2]:
    yArr.append(i)
    yLen += 1

# create x matrix
# if there are n pairs, will create a n x 2 matrix for x matrix
xMat = createXMatrix(xLen, 2, xArr)

# create y matrix
yMat = createYMatrix(yLen, yArr)

# create transpose matrix of x
xTranspose = transposeMat(xMat)

# multiply matrices
#X^t X and X^t Y
xTx = multiplyMatrices(xTranspose, xMat)
xTy = multiplyMatrices(xTranspose, yMat)


# get the final matrix and print
#(X^t X)^-1 * X^t Y
xTxInverse = np.linalg.inv(xTx)
finalMat = multiplyMatrices(xTxInverse, xTy)
print("---------------FINAL MATRIX------------------")
print(finalMat)
print("----------------------------------------------")
print()

# print linear equation
x = round(float(finalMat[1]), 2)
y = round(float(finalMat[0]), 2)
print("---------------LINEAR EQUATION-----------------")
print("y = %.1fx + %.1f" % (x, y))
print("-----------------------------------------------")
print()
# print graph
# points for scatter plot and line of fit
xLine = np.linspace(-1,40)
yLine = x*xLine + y
xPoint = xArrNo1
yPoint = yArr

# plot points and name axes and title
plt.plot(xLine, yLine)
plt.scatter(xPoint, yPoint)

plt.title("Graph of: y = %.1fx + %.1f" % (x, y))
plt.xlabel('x')
plt.ylabel('y ')

# print
plt.show()
