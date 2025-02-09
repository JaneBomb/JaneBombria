/*
Name: Jane Bombria
Class: CS1150 (M/W)
Due: September 20, 2023
Assignment #4
This code shows that I can get a string input and put it into the char data type. I can then take that
 information and encrypt it and decrypt it, using either a Caesar cipher or a XOR encryption.
*/

import java.util.Scanner;
public class BombriaJaneAssignment4 {

	public static void main(String[] args) {
		// declare variables
		String fiveCharString = "";
		Scanner Input = new Scanner(System.in);
		// random number generator
		int randomNumber = (int)(Math.random()* 26);
		//random letter generator
		int num = 65+(int)(Math.random()*26);
		char randomLetter = (char)num;
		
		// print encryption options and get user input
		System.out.println("Encryption Program");
		System.out.println("-------------------------");
		System.out.println("1) Caesar Cipher");
		System.out.println("2) XOR Encryption");
		System.out.print("Which encryption/decryption method would you like? (1 or 2): ");
		int encryptionOption = Input.nextInt();
		
		// checks if number input is valid or invalid (1 or 2), if so asks for string input
		if (encryptionOption >= 1 && encryptionOption <= 2) {
				System.out.println();
				System.out.print("Please enter a string with exactly 5 characters: ");
				fiveCharString = Input.next();
		}
		else {
			System.out.println(encryptionOption + " is not a valid menu selection. Run again and enter 1 or 2.");
		}
		
		// changes string to lower case and checks if string is 5 characters
		fiveCharString = fiveCharString.toLowerCase();
		int length = fiveCharString.length();
		if (encryptionOption == 1 || encryptionOption == 2) {
			if (length == 5) {
				char char1 = fiveCharString.charAt(0);
				char char2 = fiveCharString.charAt(1);
				char char3 = fiveCharString.charAt(2);
				char char4 = fiveCharString.charAt(3);
				char char5 = fiveCharString.charAt(4);
				if (encryptionOption == 1) {
					// encrypts using Caesar Cipher
					char encryptedChar1 = (char)((char1 - 97 + randomNumber) % 26 + 97);
					char encryptedChar2 = (char)((char2 - 97 + randomNumber) % 26 + 97);
					char encryptedChar3 = (char)((char3 - 97 + randomNumber) % 26 + 97);
					char encryptedChar4 = (char)((char4 - 97 + randomNumber) % 26 + 97);
					char encryptedChar5 = (char)((char5 - 97 + randomNumber) % 26 + 97);
					String caesarEncrypted = "" + encryptedChar1 + encryptedChar2 + encryptedChar3
							+ encryptedChar4 + encryptedChar5;
				
					// decrypts the encrypted message
					int decryptShift = 26 - randomNumber;
					char decryptedChar1 = (char)((encryptedChar1 - 97 + decryptShift) % 26 + 97);
					char decryptedChar2 = (char)((encryptedChar2 - 97 + decryptShift) % 26 + 97);
					char decryptedChar3 = (char)((encryptedChar3 - 97 + decryptShift) % 26 + 97);
					char decryptedChar4 = (char)((encryptedChar4 - 97 + decryptShift) % 26 + 97);
					char decryptedChar5 = (char)((encryptedChar5 - 97 + decryptShift) % 26 + 97);
					String caesarDecrypted = "" + decryptedChar1 + decryptedChar2 + decryptedChar3
							+ decryptedChar4 + decryptedChar5;
					// print Caesar cipher
					System.out.println("Caesar Cipher Encryption");
					System.out.println("-------------------------------------");
					System.out.println("Caesar Shift Value (encrypt) = " + randomNumber);
					System.out.println("Caesar Shift Value (decrypt) = " + decryptShift);
					System.out.println("Original String = 	" + fiveCharString);
					System.out.println("Caesar Encrypted String = " + caesarEncrypted);
					System.out.println("Caesar Decrypted String = " + caesarDecrypted);
				}
				if (encryptionOption == 2) {
					// encrypt using XOR encryption
					char encryptedChar1 = (char)(char1 ^ randomLetter);
					char encryptedChar2 = (char)(char2 ^ randomLetter);
					char encryptedChar3 = (char)(char3 ^ randomLetter);
					char encryptedChar4 = (char)(char4 ^ randomLetter);
					char encryptedChar5 = (char)(char5 ^ randomLetter);
					String XORencrypted = "" + encryptedChar1 + encryptedChar2 + encryptedChar3
							+ encryptedChar4 + encryptedChar5;
	
					// decrypt using XOR
					char decryptedChar1 = (char)(encryptedChar1 ^ randomLetter);
					char decryptedChar2 = (char)(encryptedChar2 ^ randomLetter);
					char decryptedChar3 = (char)(encryptedChar3 ^ randomLetter);
					char decryptedChar4 = (char)(encryptedChar4 ^ randomLetter);
					char decryptedChar5 = (char)(encryptedChar5 ^ randomLetter);
					String XORdecrypted = "" + decryptedChar1 + decryptedChar2 + decryptedChar3
							+ decryptedChar4 + decryptedChar5;
				
					//print
					System.out.println("XOR Encryption");
					System.out.println("-------------------------------------");
					System.out.println("XOR Key = 		" + randomLetter);
					System.out.println("Original String =      " + fiveCharString);
					System.out.println("XOR Encrypted String = " + XORencrypted);
					System.out.println("XOR Decrypted String = " + XORdecrypted);
				}
	
			}
			else {
				System.out.println(fiveCharString + " is not a valid string - program can only encrypt strings with 5 characters.");
			}
		}

	} // end of main
} // end of class
