/*
Multiline comment
*/

// Example from https://logging.apache.org/log4j/2.x/manual/configuration.html
import com.foo.Bar;
import java.util.Scanner;

// Import log4j classes.
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;

public class SimpleLoggingExample {

    // Define a static logger variable so that it references the
    // Logger instance named "MyApp".
    private static final Logger logger = LogManager.getLogger(MyApp.class);

    public static void main(final String... args) {

        // Set up a simple configuration that logs on the console.

        logger.trace("Entering application.");
        Bar bar = new Bar();
        if (!bar.doIt()) {
            logger.error("Didn't do it.");
        }
        logger.trace("Exiting application.");
    }
    // End of example
    public void one() throws IOException {
        Scanner scanner = new Scanner(System.in);
        System.out.println("How are you doing?");
        String message = scanner.nextLine();
        System.out.print("So... you are doing ");
        System.out.println(message);
    }

    public enum Color {
        RED (1, 3),
        GREEN (2, 4);

        private final double mass;   // in kilograms
        private final double radius; // in meters
        Planet(double mass, double radius) {
            this.mass = mass;
            this.radius = radius;
        }
        private double mass() { return mass; }
        private double radius() { return radius; }

    }

    public void two(int a) {
        try {
            this.one();
        }
        catch (IOException e) {
            System.out.println("No logging!");
        }
        try {
            this.one();
        }
        catch (IOException e) {
            logger.error("Caught exception");
        }
        if (2 > 1) {
            if (3 > 2) {
                logger.info("2 > 1 and 3 > 2");
            }
            else if (4 < 3) {
                logger.info("Hiii");
            }
            else {
                logger.info("2 > 1 and 3 <= 2");
            }
        }
        switch(a) {
          case 1:
            System.out.println("Good morning");
            break;
          case 2:
            int c = 2;
            break;
          default:
            logger.error("Default");
            for (int i=0; i<5; i++) {
                System.out.println("Good night");
            }
        }
    }
}