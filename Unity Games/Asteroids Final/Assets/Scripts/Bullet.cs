using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Moves bullet and deals with collisions
/// </summary>
public class Bullet : MonoBehaviour
{
    float bulletLife = 2f;
    Timer deathTimer;

    /// <summary>
    /// Start is called before the first frame update
    /// </summary>
    void Start()
    {
        deathTimer = gameObject.AddComponent<Timer>();
        deathTimer.Duration = bulletLife;
        deathTimer.Run();
    }

    /// <summary>
    /// Update is called once per frame
    /// </summary>
    void Update()
    {
        // destroys after 2 sec
        if (deathTimer.Finished)
        {
            Destroy(gameObject);
        }
    }
    /// <summary>
    /// Applies force to bullet
    /// </summary>
    /// <param name="direction"></param>
    public void ApplyForce(Vector2 direction)
    {
        const float magnitude = 6f;
        GetComponent<Rigidbody2D>().AddForce(magnitude * direction, ForceMode2D.Impulse);
    }

    /// <summary>
    /// Collision with asteroid
    /// </summary>
    /// <param name="collision"></param>
    public void OnCollisionEnter2D(Collision2D collision)
    {
        if (collision.gameObject.tag == "Asteroid")
        {
            Destroy(gameObject);
        }
    }
}
