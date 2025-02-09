using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Moves and rotates the ship
/// </summary>
public class Ship : MonoBehaviour
{
    [SerializeField]
    GameObject bulletPrefab;
    [SerializeField]
    GameObject HUD;

    Rigidbody2D rb2d;
    Vector2 thrustDirection;

    const float ThrustForce = 5;
    const int RotateDegreesPerSecond = 100;

    /// <summary>
    /// Start is called before the first frame update
    /// </summary>
    void Start()
    {
        rb2d = GetComponent<Rigidbody2D>();
        thrustDirection = new Vector2(1, 0);
    }
    /// <summary>
    /// Update happens once per frame
    /// </summary>
    void Update()
    {
        // rotates ship based on user input
        float rotationAmount = RotateDegreesPerSecond * Time.deltaTime;
        if (Input.GetAxis("Rotate") != 0)
        {
            if (Input.GetAxis("Rotate") < 0)
            {
                rotationAmount *= -1;
            }
            else
            {
                rotationAmount *= 1;
            }
            transform.Rotate(Vector3.forward, rotationAmount);

            // moves ship in direction ship is facing
            Vector3 euler = transform.eulerAngles;
            float angleZ = Mathf.Deg2Rad * euler.z;
            thrustDirection.x = Mathf.Cos(angleZ);
            thrustDirection.y = Mathf.Sin(angleZ);
        }

        // shoot bullets
        Vector2 shipPosition = gameObject.transform.position;
        if (Input.GetKeyDown(KeyCode.LeftControl))
        {
            // play sound
            AudioManager.Play(AudioClipName.PlayerShot);

            // instantiate bullets to ship position
            GameObject bullet = Instantiate(bulletPrefab);
            bullet.transform.position = shipPosition;

            // apply force to bullet
            Bullet bulletScript = bullet.GetComponent<Bullet>();
            bulletScript.ApplyForce(thrustDirection);

        }
    }

    /// <summary>
    /// Adds force to the ship to move it
    /// </summary>
    void FixedUpdate()
    {
        if (Input.GetAxis("Thrust") > 0)
        {
            rb2d.AddForce(thrustDirection * ThrustForce, ForceMode2D.Force);
        }
    }

    /// <summary>
    /// Destroy ship when it collides with asteroid
    /// </summary>
    /// <param name="collision"></param>
    private void OnCollisionEnter2D(Collision2D collision)
    {
        if (collision.gameObject.tag == "Asteroid")
        {
            HUD.GetComponent<HUD>().StopGameTimer();

            // play sound and destory ship
            AudioManager.Play(AudioClipName.PlayerDeath);
            Destroy(gameObject);
        }
    }
}

