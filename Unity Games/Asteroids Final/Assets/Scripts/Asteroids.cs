using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Sets asteroid sprite and moves it
/// </summary>
public class Asteroids : MonoBehaviour
{
    [SerializeField]
    Sprite blueSprite;
    [SerializeField]
    Sprite greenSprite;
    [SerializeField]
    Sprite yellowSprite;

    AsteroidSpawner spawn;

    /// <summary>
    /// Start is called before the first frame update
    /// </summary>
    void Start()
    {
        spawn = Camera.main.GetComponent<AsteroidSpawner>();
        // choose random sprite
        SpriteRenderer spriteRenderer = gameObject.GetComponent<SpriteRenderer>();
        int spriteNumber = Random.Range(0, 3);
        if (spriteNumber == 0)
        {
            spriteRenderer.sprite = blueSprite;
        }
        else if (spriteNumber == 1)
        {
            spriteRenderer.sprite = greenSprite;
        }
        else
        {
            spriteRenderer.sprite = yellowSprite;
        }
    }
    /// <summary>
    /// select direction and angle to move
    /// </summary>
    public void Initialize(Direction direction, Vector3 location)
    {
        // spawn location for asteroid
        transform.position = location;

        // randomly select impulse force to apply
        float angle;
        float randomAngle = Random.value * 30f * Mathf.Deg2Rad;

        if (direction == Direction.Up)
        {
            angle = 75 * Mathf.Deg2Rad + randomAngle;
        }
        else if (direction == Direction.Left)
        {
            angle = 165 * Mathf.Deg2Rad + randomAngle;
        }
        else if (direction == Direction.Right)
        {
            angle = -15 * Mathf.Deg2Rad + randomAngle;
        }
        else
        {
            angle = 255 * Mathf.Deg2Rad + randomAngle;
        }

        // apply impulse force to get asteroid moving
        StartMoving(angle);
    }

    public void StartMoving(float angle)
    {
        // apply impulse force to get asteroid moving
        const float MinImpulseForce = 1f;
        const float MaxImpulseForce = 2f;
        Vector2 moveDirection = new Vector2(
            Mathf.Cos(angle), Mathf.Sin(angle));
        float magnitude = Random.Range(MinImpulseForce, MaxImpulseForce);
        GetComponent<Rigidbody2D>().AddForce(
            moveDirection * magnitude,
            ForceMode2D.Impulse);
    }
    /// <summary>
    /// Collision with bullet
    /// </summary>
    /// <param name="collision"></param>
    public void OnCollisionEnter2D(Collision2D collision)
    {
        Vector3 localScale = transform.localScale;
        CircleCollider2D collider = gameObject.GetComponent<CircleCollider2D>();

        if (collision.gameObject.tag == "Bullet")
        {
            // destroy if asteroid has been split twice
            if (localScale.x < 0.5)
            {
                // play sound
                AudioManager.Play(AudioClipName.AsteroidHit);
                Destroy(gameObject);
            }
            else
            {
                // create two new asteroids
                gameObject.transform.localScale = localScale / 2;
                collider.radius = 1;
                for (int i = 1; i <= 2; i++)
                {
                    // play sound
                    AudioManager.Play(AudioClipName.AsteroidHit);

                    // move new asteroids
                    GameObject newAsteroid = Instantiate(gameObject);
                    Asteroids script = newAsteroid.GetComponent<Asteroids>();
                    script.StartMoving(Random.Range(0, 2 * Mathf.PI));
                }
                Destroy(gameObject);
            }
        }
    }
}
