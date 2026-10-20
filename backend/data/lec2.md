---
source: Lecture_02_-_Classes_and_Objects.pdf
course: Object Oriented Programming IT2030 (SLIIT - Faculty of Computing)
lecture_id: lec2
module_id: module1      # suggested tag, change to match your taxonomy
slides: 1-58
conversion: text copied from the PDF text layer; images and diagrams described in short [Diagram: ...] or [Image: ...] notes; code that was cut off, folded or incomplete on the slide was completed and marked with [completed], [reconstructed] or [corrected] notes; all Java and C++ code blocks on slides 13, 17, 35, 39, 40, 48, 49, 54 were compiled and run
---

## Slide 1
IT2030 - Object Oriented Programming
Lecture 02
Java Classes and Objects

## Slide 2
Learning Outcomes
At the end of the Lecture students should be able to get a revision on OOC you learnt in Year 1
- Object Oriented Programming
- Classes and Objects
- Abstraction
- Encapsulation
- Inheritance
- Polymorphism
- Interfaces
- We will also look at key differences between writing Simple Object Oriented Programs in C++ and Java.

## Slide 3
Object Oriented Programming
- Object Oriented programming is a method of implementation in which programs are organized as cooperative collections of objects, each of which represents an instance of some class, and whose classes are all members of a hierarchy of classes united via inheritance relationships.

(Reference : Grady Booch, eta (2008), Object Oriented Analysis and Design with Applications 3rd Edition, pg 41)

## Slide 4
Object Oriented Programming
- Object Oriented Programming is a method of implementation in which programs are organized as a collection of objects which cooperate to solve a problem.
- Allows to solve more complex problems easily

## Slide 5
Object Oriented Programming
- A complex system is developed using smaller sub systems
- Sub systems are independent units containing their own data and functions
- Can reuse these independent units to solve many different problems

## Slide 6
A Computer System
[Diagram: picture titled "Basic parts of a Computer" with labels Printer, Monitor, C.P.U, Speakers, Speakers, Keyboard and Mouse. An arrow points from the computer to a second picture showing the internal components of a computer (motherboard and other parts).]

## Slide 7
Classes
- A class is the abstract definition of the data type. It includes the data elements that are part of the data type, and the operations which are defined on the data type.
- It is an Entity which could be a thing, person or something that is imaginary.

## Slide 8
Classes
- An entity can be described by the data ( Properties ) and its behavior ( methods )
[Diagram: a table with three parts labelled "Class Name", "Attributes/Properties" and "Methods".]
e.g.:
[Diagram: a car drawn as a class. Label "class car". Methods box: refuel() getFuel setSpeed() getSpeed() drive(). Attributes box: fuel, maxspeed.]

## Slide 9
Classes and Objects
- An Object is a specific instance of the data type (class)
- A class is a blue print of an object.
[Diagram: a house floor plan labelled "Class House", and three pictures of houses labelled House1, House2 and House3, with the label "Objects".]

## Slide 10
Objects
- Objects are instances of classes, which we can use to store data and perform actions
- We need to define a class including the properties and methods and then create as many objects which has the same structure of the class ( House example )

## Slide 11
Class in C++
[Diagram: a class box named Student with attributes StudentNo, Name, CA_marks, Final_mark, Total marked Private, and methods assignMarks(), calculateTotal(), printDetails() marked Public. Next to it is the matching C++ code:]
```cpp
class Student{
   private :
           int studentNo;
           char name[30];
           int CA_mark;
           int Final_mark;
   public:
           void assignMarks(int pCA, int pFin);
           int calculateTotal();
           void printDetails();
};
```

## Slide 12
Exercise 1
- Identify the classes, attributes and what sort of objects that will have for hospital management system
- Write the classes and possible methods in simple English language

## Slide 13
Class in Java
C++:
```cpp
class Student{
   private :
       int studentNo;
       char name[30];
       int CA_mark;
       int Final_mark;
   public:
       void assignMarks(int pCA, int pFin) {
       }
       int calculateTotal() {
       }
       void printDetails() {
       }
};
```
Java:
```java
class Student {
    private int studentNo;
    private String name;
    private int CA_mark;
    private int Final_mark;
    public void assignMarks(int pCA,
                   int pFin) {
    }
    public int calculateTotal() {
        return 0;
    }
    public void printDetails() {
    }
}
```
[corrected: the Java version on the slide has an empty body for calculateTotal(), which has return type int, so it would not compile. A return statement was added. The C++ version is shown exactly as on the slide and compiles with a warning only. Both columns are labelled C++ and Java on the slide.]

## Slide 14
Java vs C++
- All methods are implemented in the class definition in Java.
- Each property, method needs a specific access modifier e.g. private, public, protected
- In Java there is no semi colon at the end of the class
- In Java you only have dynamic objects.
- Since Java has an automatic garbage collector, you do not need to use a command line delete to remove objects from memory.
- We use the dot operator instead of the -> operator to access methods in Java.

## Slide 15
Private & Public
- The private part of the definition specifies the data members of a class
- These are hidden from outside the class and can only be accessed though the operations defined for the class
- The public part of the definition specifies the operations as function prototypes
- These operations, or methods as they are called, can be accesses by the main program.

## Slide 16
Private & Public
[Diagram: a "Client" on the left connects to the Public part (assignMarks(), calculateTotal(), printDetails()) of an object called student1. The Private part of student1 holds studentID, name, CA_marks, Final_mark and Total.]

## Slide 17
Creating Objects
```java
class Student {
    private int studentNo;
    private String name;
    private int CA_mark;
    private int Final_mark;
    public void assignMarks(int pCA,
                   int pFin) {
    }
    public int calculateTotal() {
        return 0;
    }
    public void printDetails() {
    }
}
public class StudentApp {
    public static void main(String args[]) {
        Student student1 = new Student();
        Student student2 = new Student();
        // We do not use * for pointers in Java
    }
}
```
[completed: the slide shows only the two object creation lines and a comment. The Student class from slide 13 (with the return statement added) and a class with a main method were added so the program is whole. Verified to compile and run.]
[Diagram: two object boxes. student1: studentNo - 1011, Name - Ajith Silva, CA_mark - 56, Final_mark -60. student2: studentNo - I131, Name - Surani Fernando, CA_mark - 70, Final_mark -65.]

## Slide 18
Exercise 2
- Select one class that selected from the hospital management system. Ex:- receptionist
- Write the relevant class using the java language

## Slide 19
Methods and Properties
- In C++ properties are called data members, other popular names for properties are attributes, variables.
- In C++ methods are called member functions, other popular names are operations, behaviors. These are really functions.

## Slide 20
Abstraction
- An abstraction denotes the essential characteristics of an object that distinguish it from all other kinds of objects and thus provide crisply defined conceptual boundaries, relative to perspective of the viewer.
- (Reference : Grady Booch, eta (2008), Object Oriented Analysis and Design with Applications 3rd Edition, pg 44)

## Slide 21
Abstraction
- Abstraction is the process of removing characteristics from 'something' in order to reduce it to a set of essential characteristics that is needed for the particular system.

## Slide 22
Abstraction
[Diagram: a cartoon of a cat seen by two people. One person imagines a furry, purring cat; the other imagines the cat's internal organs (labelled kidney, stomach, intestine, heart, lung, bladder, liver). Caption: "Abstraction focuses on the essential characteristics of some object, relative to the perspective of the viewer."]

## Slide 23
Exercise 3
Think of the class you selected in Hospital Management System.
1. What are the attributes needed ?
2. What are the attributes that can be omitted?

## Slide 24
Encapsulation
- Encapsulation is the process of compartmentalizing the elements of an abstraction that constitute its structure and behavior; encapsulation serves to separate the contractual interface of an abstraction and its implementation.
- (Reference : Grady Booch, eta (2008), Object Oriented Analysis and Design with Applications 3rd Edition, pg 52)

## Slide 25
Encapsulation
[Diagram: a drawing of a cat with a panel open on its side showing machinery inside, with parts labelled such as PURRER and POUNCER. Caption: "Encapsulation hides the details of the implementation of an object".]

## Slide 26
Encapsulation
- It is the process of grouping related attributes and methods together, giving a name to the unit and providing an interface for outsiders to communicate with the unit.

## Slide 27
Exercise 4
- Explain what is encapsulation with related to your class in the Hospital Management System.

## Slide 28
Information Hiding
- Hide certain information or implementation decision that are internal to the encapsulation structure ( class )
- The only way to access an object is through its public interface
  - Public - anyone can access / see it
  - Private - no one except the class can see/ use it

## Slide 29
Exercise 5
- Modify your java classes so that it support for information hiding

## Slide 30
Interface
[Diagram: a car in the centre, with arrows from a steering wheel, an accelerator pedal and a gear stick pointing to it.]

## Slide 31
Interface
[Diagram: a "Client" on the left uses the public methods setOtDetails(), setAllowance(), calcSal() and printPaySlip() of an Employee object. The Employee holds EmployeeNo, Name, Basic Salary, OT Hours, OT Amount, Allowance and Salary.]

## Slide 32
Terminology
[Diagram: a class box named Employee. Its attributes are empNo, name, basicSalary, otHrs, otRate, allowance, salary. Then Employee(empNo, name, basicSalary) and the methods setOtDetails(), setAllowance(), calcSalary(), printPaySlip(). Labels on the right: "Class name" for Employee; "Attributes", "Properties", "Data Members" for the attribute list; "Methods", "Behaviors", "member functions" for the method list.]

## Slide 33
Exercise 6
Implement a class called MyMain with a main method and Create Objects of the class to demonstrate the methods.

## Slide 34
Constructor
- The constructor is used to initialize the object when it is declared.
- The constructer does not return a value, and has no return type ( not even void )
- The constructors has the same name as the class.
- There can be default constructers or constructors with parameters
- When an object is declared the appropriate constructor is executed.

## Slide 35
Constructor
```java
public class Rectangle {
    private int width;
    private int length;

    // default Constructor
    public Rectangle () {
        width = 0;
        length = 0;
    }

    // Constructor with parameters
    public Rectangle (int w, int l) {
        width = w;
        length = l;
    }

    public static void main(String args[]) {
        // default constructor called
        Rectangle r1 = new Rectangle();
        // Second constructor called
        Rectangle r2 = new Rectangle(10,20);
    }
}
```
[completed: the slide shows the two constructors in one column and the main method in another. The class declaration, the width and length fields, and the closing braces were added so the program is whole. In the slide the main method appears next to the constructors. Verified to compile and run.]

## Slide 36
Constructors
- Default Constructors
  - Can be used to initialized attributes to default values
```java
public Rectangle () {
  width = 0;
  length = 0;
}
```
- Overloaded Constructors ( Constructors with Parameters )
  - Can be used to assign values sent by the main program as arguments
```java
public Rectangle (int w, int l) {
  width = w;
  length = l;
}
```
[note: these are parts of the Rectangle class shown whole on slide 35.]

## Slide 37
Exercise 7
Take one class from your topic
1. Add the default constructor
2. And a parameterized constructor to initiate all attributes

## Slide 38
Getters and Setters
- In general properties are declared as private preventing them from being accessed from outside the class.
- Typically an attribute will have a getter (accessor) (A get method to return its value) and a setter (mutator) (A set method to set a value).
- e.g. a property called length will have a getter defined as int getLength() and a setter defined as void setLength(). Both these methods will be declared as public methods.

## Slide 39
Getters and Setters
```java
public class Rectangle {
    private int width;
    private int length;

    // Constructors
    public Rectangle() {
        width = 0;
        length = 0;
    }
    public Rectangle(int w, int l) {
        width = w;
        length = l;
    }
    // public
    public void setWidth(int w) {
        if (w > 0)
            width = w;
        else
            width = 10;
    }
    public int getWidth() {
        return width;
    }
}
```
[completed: the slide shows lines 4 to 25 of a Rectangle class, with the constructor bodies folded and hidden. The class declaration and closing brace were added, and the folded constructor bodies were filled in from slide 35. Only setWidth and getWidth appear on the slide. Verified to compile.]

## Slide 40
this keyword
- The this keyword can be used to refer to any member of the current object from within an instance Method or a constructor.
```java
public class Employee {
    private int employeeNo;
    private String name;
    private double basicSalary;

    public Employee(int pempno, String name, double pbasicSal) {
        employeeNo = pempno;
        this.name = name;
        basicSalary = pbasicSal;
    }
}
```
- We need to use this.name to refer to the property name to distinguish it from the parameter name.
[completed: the slide shows only the constructor. The class declaration and the three field declarations (employeeNo, name, basicSalary) were added, with types inferred from the constructor parameters. Verified to compile.]

## Slide 41
Exercise 8
- Modify your class with getters and setters

## Slide 42
Generalization/Inheritance
- Child class is a type of the parent class
- Used to showcase reusable elements in the class diagram
- Child classes "inherit" the attributes and methods defined in the parent class
[Diagram: a class diagram with Shape at the top and two child classes, Rectangle and Circle, below it.]

## Slide 43
C++ vs Java - Inheritance
C++:
```cpp
class Circle : public Shape {
```
Java:
```java
class Circle extends Shape {
```
Java has a simpler inheritance mechanism where base class is extended as public.
C++ has multiple inheritance compared to Java's Single Inheritance.

## Slide 44
C++ vs Java - Inheritance
C++:
```cpp
Circle (string tname, int r) : Shape ( tname) {
         radius = r;
}
```
Java:
```java
public Circle (String tname, int r) {
    super(tname);
    radius = r;
}
```
When you want to call a base class constructor C++ Requires to explicitly name the base class. In Java we use the super keyword to access the direct descendent class.
However this implies that in Java you can't directly call a class higher in the hierarchy e.g. the Grandfather class which is not in C++
[note: these are parts of the Shape example on slides 48 and 49.]

## Slide 45
C++ vs Java - Inheritance
C++:
```cpp
virtual void speak() {}
```
Java:
```java
public void speak() {}
```
All methods in Java are virtual by default. In C++ we need to explicitly define polymorphic methods.

## Slide 46
Exercise 9
Think of a way of implementing generalization in you selected class

## Slide 47
Object Class
[Diagram: a family tree of dog breeds. At the top is a gray wolf labelled "Gray wolf (Common ancestor)". Below it four regions labelled Europe, North America, China and India, each with many dog breeds branching from it.]
- A class hierarchy is similar to the taxonomy of animals that shows their ancestry.
- There are many breeds of dogs. A well known fact is that the common origin of a dog is the Gray Wolf.
- All Java classes are derived from a class called Object. This includes all the existing Java built in classes and the classes that you write. The methods and properties of the Object class is accessible to any Java class that you create.

## Slide 48
Inheritance Shapes Example C++
```cpp
#include <iostream>
#include <string>
using namespace std;

class Shape {
    protected:
    string name;
    public:
    Shape() {}
    Shape (string tname) {
        name = tname;
    }
    virtual void print() {
        cout << "Shape name : " << name << endl;
    }
    virtual int area() { return 0; }
};

class Rectangle: public Shape{
    protected:
    int width;
    int height;
    public :
    Rectangle (string tname, int w, int h) : Shape ( tname)
    {
            width = w;
            height = h;
        }
    int area( )
    {
        return width * height;
    }
};

class Circle: public Shape{
    protected:
    int radius;
    public :
    Circle (string tname, int r) : Shape ( tname)
    {
            radius = r;
        }
    int area( )
    {
        return (int)(22.0 / 7 * radius * radius);
    }
};

int main() {
    Rectangle R("Rectangle", 4 , 6);
    Circle C("Circle", 3 );
    R.print();
    cout << R.area() << endl;
    C.print();
    cout << C.area() << endl;
    return 0;
}
```
File: Shape_example.cpp
[reconstructed: the slide shows only lines 23 to 33, from the start of class Rectangle to the line "int area( )", and is cut off there. Added: the Shape class (name, constructors, virtual print and area), the body of area for Rectangle, the Circle class, and a main function. The hidden lines are written to match the Java version on slide 49. The exact original wording of the hidden lines is not visible. Verified to compile and run.]

## Slide 49
Inheritance Shapes Example Java
```java
class Shape {
    protected String name;
    public Shape() {};
    public Shape (String tname) {
        name = tname;
    }
    public void print() {
        System.out.println("Shape name : " + name);
    }
    public int area(){ return 0;}
}
class Rectangle extends Shape {
    protected int width;
    protected int height;
    public Rectangle (String tname, int w, int h) {
        super(tname);
        width = w;
        height = h;
    }
    public int area() {
        return width * height;
    }
}
class Circle extends Shape {
    protected int radius;
    public Circle (String tname, int r) {
        super(tname);
        radius = r;
    }
    public int area() {
        return (int)(22.0 / 7 * radius * radius);
    }
}
class ShapeApp {
    public static void main(String args[]) {
    Rectangle R = new Rectangle("Rectangle", 4 , 6);
    Circle C = new Circle("Circle", 3 );
    R.print();
    System.out.println(R.area());
    C.print();
    System.out.println(C.area());
    }
}
```
File: Shape_example.java
[reconstructed: the slide shows only the Shape class outline, the headings of Rectangle, Circle and ShapeApp, and the first lines of main. The bodies of the Shape constructor, print() and the Rectangle and Circle classes are folded (hidden) on the slide, and main is cut off after the line creating the Circle. Added: the folded bodies, the area methods, and the print and area calls at the end of main. The exact original wording is not visible. Verified to compile and run.]

## Slide 50
Exercise 10
Write the java code in order to implement the inheritance

## Slide 51
Polymorphism
- Greek meaning "having multiple forms"
- Ability to assign a different meaning or usage to something in different contexts
- Specifically, to allow an entity such as a variable, a function, or an object to have more than one form

## Slide 52
An example
- Consider the request (analogues to a method) "please cut this in half" taking many forms
[Image: a photo of a cake being cut.]

## Slide 53
"please cut this in half"
- Imagine this task is automated...
- Without polymorphism
  - Need to tell the computer how to proceed for each situation
- With polymorphism
  - Just tell please cut this in half
  - The computer will handle the rest!

## Slide 54
Animal Example
```java
class Animal {
    protected String name;
    public Animal(String n) {
        name = n;
    }
    public void song() {
        System.out.println(name + " does not make a sound");
    }
}
class Cat extends  Animal {
    public Cat(String n) {
        super(n);
    }
    public void song() {
        System.out.println(name + " says meow");
    }
}
class Dog extends Animal {
    public Dog(String n) {
        super(n);
    }
    public void song() {
        System.out.println(name + " says woof");
    }
}
class Cow extends Animal {
    public Cow(String n) {
        super(n);
    }
    public void song() {
        System.out.println(name + " says moo");
    }
}
class AnimalApp {
    public static void main(String args[]) {
    Animal ani[] = new Animal[4];
    ani[0] = new Cat("Micky the Cat");
    ani[1] = new Dog("Rover the Dog");
    ani[2] = new Cow("roo the Cow");
    ani[3] = new Animal("no name");
    for (int r=0;r<4; r++)
        ani[r].song();
    }
}
```
Files: Animal_example.cpp, Animal_example.java
[reconstructed: the slide shows only the Animal, Cat, Dog and Cow class headings (their bodies are folded and hidden) and the AnimalApp main method, which is cut off after the loop line. Added: the constructors and song() methods, and the closing braces. The exact original wording of song() is not visible. Only the Java code is shown on the slide, even though both file names are listed. Verified to compile and run.]

## Slide 55
Exercise 11
- Think of a way to implement Polymorphism in your solution

## Slide 56
Exercise 12
Implement the necessary classes, along with their required attributes and methods, based on the following description.
You have been assigned the task of developing a simple system to manage the employees of a company. The system should consist of two classes, Employee and Manager. The Employee class should have three data members, EmpId, name, and address, which are all of string data type. It should also have a default constructor and a parameterize constructor to initialize these attributes.
Create a getter and a setter to the attribute EmpId. Add two methods, Read () and Print(). The Read () should accept inputs for the above mentioned attributes through the keyboard and Print() should display their values.

## Slide 57
Exercise 12 (continued)
The Manager class should extend from the Employee class and should have two data members Department number (int), Department name (String). It should have a parameterized constructor to initialize all these attributes.
Furthermore, you need to create a class called EmployeeApp with a main method where you can create 2 objects each from Employee and Manager classes.

## Slide 58
Thank you!
