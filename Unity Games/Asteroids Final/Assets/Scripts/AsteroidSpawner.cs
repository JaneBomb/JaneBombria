using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Spawns an asteroid
/// </summary>
public class AsteroidSpawner : MonoBehaviour
{
    [SerializeField]
    GameObject prefabAsteroid;

    GameObject asteroid;
    CircleCollider2D asteroidCollider;

    Asteroids asteroidScript;

    /// <summary>
    /// Start is called before the first frame update
    /// </summary>
    void Start()
    {
        // instantiate top asteroid
        asteroid = Instantiate(prefabAsteroid);
        asteroidCollider = GetComponent<CircleCollider2D>();
        asteroidScript = asteroid.GetComponent<Asteroids>();
        asteroidScript.Initialize(Direction.Down, new Vector3(0, ScreenUtils.ScreenTop + 1, 0));

        // instantiate right asteroid
        asteroid = Instantiate(prefabAsteroid);
        asteroidCollider = GetComponent<CircleCollider2D>();
        asteroidScript = asteroid.GetComponent<Asteroids>();
        asteroidScript.Initialize(Direction.Right, new Vector3(ScreenUtils.ScreenRight + 1, 0, 0));

        // instantiate left asteroid
        asteroid = Instantiate(prefabAsteroid);
        asteroidCollider = GetComponent<CircleCollider2D>();
        asteroidScript = asteroid.GetComponent<Asteroids>();
        asteroidScript.Initialize(Direction.Left, new Vector3(ScreenUtils.ScreenLeft - 1, 0, 0));

        // instantiate bottom asteroid
        asteroid = Instantiate(prefabAsteroid);
        asteroidCollider = GetComponent<CircleCollider2D>();
        asteroidScript = asteroid.GetComponent<Asteroids>();
        asteroidScript.Initialize(Direction.Up, new Vector3(0, ScreenUtils.ScreenBottom - 1, 0));
    }
}
