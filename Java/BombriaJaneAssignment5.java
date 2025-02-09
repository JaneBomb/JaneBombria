/*
 * Name: Jane Bombria
 * Class: CS 1450 (M/W)
 * Due Date: 2/28/24
 * Assignment #5
 * I can use and manipulate stacks and create my own generic method.
 */
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Scanner;
import java.util.Stack;

public class BombriaJaneAssignment5 {

	public static void main(String[] args) throws IOException {
		// PART 1 - JCF stack
		// create stack with array values
		int[] values = {10, 27, 19, 45, 4, 2, 82, 49};
		Stack<Integer> stack = new Stack<>();
		for(int i = 0; i < values.length; i++) {
			int num = values[i];
			stack.push(num);
		}

		// find second largest number in stack and print
		int secondLargestNum = findSecondLargest(stack);
		System.out.println("Stack Values and Second to Largest Value");
		System.out.println("---------------------------------------------");
		printStack(stack);
		System.out.println("Second largest value: " + secondLargestNum);
		System.out.println();
		

		// PART 2 - Creating GenericClass
		// Create stack 1 and fill from file
		GenericStack<Integer> stack1 = new GenericStack<>();
		File numbers1 = new File ("numbers1.txt");
		Scanner readNumbers1 = new Scanner(numbers1);
		while(readNumbers1.hasNext()) {
			int num = readNumbers1.nextInt();
			stack1.push(num);
		}
		
		// Create stack 2 and fill from file
		GenericStack<Integer> stack2 = new GenericStack<>();
		File numbers2 = new File ("numbers2.txt");
		Scanner readNumbers2 = new Scanner(numbers2);
		while(readNumbers2.hasNext()) {
			int num = readNumbers2.nextInt();
			stack2.push(num);
		}
		
		// print both stacks
		System.out.println("Numbers stack 1 - filled with values from numbers1.txt");
		System.out.println("---------------------------------------------");
		printStack(stack1);
		System.out.println("Numbers stack 2  - filled with values from numbers2.txt");
		System.out.println("---------------------------------------------");
		printStack(stack2);
		
		// combine stacks and print
		GenericStack<Integer> merged = new GenericStack<>();
		mergeStacks(stack1, stack2, merged);
		System.out.println("Merged stack - largest value on top");
		System.out.println("---------------------------------------------");
		printStack(merged);
		
		// find duplicate values
		System.out.println("Details about duplicate values");
		System.out.println("---------------------------------------------");
		displayDuplicateCount(merged);
		
		
		// REPEAT PART 2 - Using generic methods with strings
		// Create stack 1 and fill from file
		GenericStack<String> stringStack1 = new GenericStack<>();
		File mountains1 = new File ("mountains1.txt");
		Scanner readMountains1 = new Scanner(mountains1);
		while(readMountains1.hasNext()) {
			String name = readMountains1.nextLine();
			stringStack1.push(name);
		}
		
		// Create stack 2 and fill from file
		GenericStack<String> stringStack2 = new GenericStack<>();
		File mountains2 = new File ("mountains2.txt");
		Scanner readMountains2 = new Scanner(mountains2);
		while(readMountains2.hasNext()) {
			String name = readMountains2.nextLine();
			stringStack2.push(name);
		}
		
		// print both stacks
		System.out.println("String stack 1 - filled with values from mountains1.txt");
		System.out.println("---------------------------------------------");
		printStack(stringStack1);
		System.out.println("String stack 2 - filled with values from mountains2.txt");
		System.out.println("---------------------------------------------");
		printStack(stringStack2);
		
		// combine stacks and print
		GenericStack<String> mergedString = new GenericStack<>();
		mergeStacks(stringStack1, stringStack2, mergedString);
		System.out.println("Merged stack - largest value on top");
		System.out.println("---------------------------------------------");
		printStack(mergedString);
		
		// find duplicate values
		System.out.println("Details about duplicate values");
		System.out.println("---------------------------------------------");
		displayDuplicateCount(mergedString);
		
		
} // main
	public static int findSecondLargest (Stack<Integer> stack) {
		// sort stack in order onto temporary stack
		Stack<Integer> temp = new Stack<>();
		int size = stack.size();
		int largest = 0;
		int secondLargest = 0;
		// finds the largest number
		// pops and pushes numbers onto temp
		for(int i = 0; i < size; i++) {
			int peek = stack.peek();
			if(peek > largest) {
				largest = peek;
			}
			int num = stack.pop();
			temp.push(num);
		}
		// finds second largest number
		// pops and pushes numbers onto stack
		int tempSize = temp.size();
		for(int i = 0; i < tempSize;i++) {
			int peek = temp.peek();
			if(peek > secondLargest && peek < largest) {
				secondLargest = peek;
			}
			int num = temp.pop();
			stack.push(num);
		}
		return secondLargest;
	}
	public static void printStack (Stack<Integer> stack) {
		Stack<Integer> temp = new Stack<>();
		// pops and pushes values to print
		int size = stack.size();
		for(int i = 0; i < size; i++) {
			int pop = stack.pop();
			System.out.println(pop);
			temp.push(pop);
		}
	}
	public static <E> void printStack (GenericStack<E> stack ) {
		GenericStack<E> temp = new GenericStack<>();
		// pops and pushes values onto temp to print
		int size = stack.getSize();
		for(int i = 0; i < size; i++) {
			E pop = stack.pop();
			System.out.println(pop);
			temp.push(pop);
		}
		// moves everything back onto original stack
		size = temp.getSize();
		for(int i = 0; i < size; i++) {
			E pop = temp.pop();
			stack.push(pop);
		}
		System.out.println();
	}
	public static <E extends Comparable<E>> void mergeStacks (GenericStack<E> stack1, GenericStack<E> stack2, GenericStack<E> mergedStack){
		while(!(stack1.isEmpty()) && !(stack2.isEmpty())) {
			E topElement1 = stack1.peek();
			E topElement2 = stack2.peek();
			int comparedValue = topElement1.compareTo(topElement2);
			// if compared value is less than other, put on bottom
			if(comparedValue <= -1) {
				E value = stack1.pop();
				mergedStack.push(value);
			}
			// if compared value is greater than other, put on top
			else if (comparedValue >= 1){
				E value = stack2.pop();
				mergedStack.push(value);
			}
				// if compared values are the same, print both
			else {
				E value1 = stack1.pop();
				E value2 = stack2.pop();
				mergedStack.push(value1);
				mergedStack.push(value2);
			}	
		}
		// runs through rest of non-empty stack
		while(!stack1.isEmpty()) {
			E value = stack1.pop();
			mergedStack.push(value);
		}
		while(!stack2.isEmpty()) {
			E value = stack2.pop();
			mergedStack.push(value);
		}
	}
	public static <E extends Comparable<E>> void displayDuplicateCount(GenericStack<E> duplicatesStack) {
		// finds and prints values with duplicates (count > 1)
		while(!duplicatesStack.isEmpty()){
			E duplicateValue = duplicatesStack.pop();
			int dupeCount = 1;
			int size = duplicatesStack.getSize();
			for(int i = 0; i< size; i++) {
				E currentValue = duplicatesStack.pop();
				int compare = duplicateValue.compareTo(currentValue);
				if(compare == 0) {
					dupeCount++;
				}
				else {
					duplicatesStack.push(currentValue);
				}
			}
			if(dupeCount > 1) {
				System.out.println("The value " + duplicateValue + " appears " + dupeCount + " times on the duplicate stack.");
			}
		}
	}

}// assignment class

class GenericStack<E>{
	private ArrayList<E> list;
	
	// constructor
	public GenericStack() {
		list = new ArrayList<>();
	}
	
	// methods
	public boolean isEmpty() {

		return list.isEmpty();

	}
	public int getSize() {
		return list.size();
		
	}
	public E peek() {
		return list.get(getSize() - 1);
	}
	public E pop() {
		E value = list.remove(getSize()-1);
		return value;
	}
	public void push(E value) {
		list.add(value);
	}
}
