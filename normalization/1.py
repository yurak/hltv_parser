import math
import unittest
from termcolor import colored

def solve_quadratic(a, b, c):
    """
    Розв’язує квадратне рівняння ax^2 + bx + c = 0
    """
    if a == 0:
        raise ValueError("Коефіцієнт 'a' не може бути нулем у квадратному рівнянні")
    
    discriminant = b ** 2 - 4 * a * c
    
    if discriminant > 0:
        root1 = (-b + math.sqrt(discriminant)) / (2 * a)
        root2 = (-b - math.sqrt(discriminant)) / (2 * a)
        return (root1, root2)
    elif discriminant == 0:
        root = -b / (2 * a)
        return (root,)
    else:
        return ()  # Немає дійсних коренів

class TestQuadraticSolver(unittest.TestCase):
    def test_two_real_solutions(self):
        self.assertEqual(solve_quadratic(1, -3, 2), (2.0, 1.0))
    
    def test_one_real_solution(self):
        self.assertEqual(solve_quadratic(1, -2, 1), (1.0,))
    
    def test_no_real_solutions(self):
        self.assertEqual(solve_quadratic(1, 0, 1), ())
    
    def test_invalid_a(self):
        with self.assertRaises(ValueError):
            solve_quadratic(0, 2, 1)

if __name__ == "__main__":
    unittest.main()
