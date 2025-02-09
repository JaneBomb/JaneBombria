// 1/29/2025
// This program will take in user input and calculate the kinetic energy based on inputs.
// This program will also use a function.

# include <iostream>
# include <string>
using namespace std;

// prototypes
double kineticEnergy(double, double);

int main(){
double mass, velocity;

// get input for mass
cout << "Enter in a number for mass (kilograms): ";
cin >> mass;

// get input for velocity
cout << "Enter in a number for velocity: ";
cin >> velocity;

// display kinetic energy
cout << "The kinetic energy is " << kineticEnergy(mass, velocity) << " joules. \n";
}

double kineticEnergy(double mass, double velocity){

    return ((0.5 * mass) * (velocity * velocity));
}