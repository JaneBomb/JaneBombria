using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Wraps object on screen
/// </summary>
public class ScreenWrapping : MonoBehaviour
{
    Rigidbody2D rb2d;
    CircleCollider2D cc2d;
    float radius;

    /// <summary>
    /// Start is called before the first frame update
    /// </summary>
    void Start()
    {
        rb2d = GetComponent<Rigidbody2D>();
        cc2d = GetComponent<CircleCollider2D>();
        radius = cc2d.radius;
    }

    /// <summary>
    /// Wraps object on screen
    /// </summary>
    void OnBecameInvisible()
    {
        Vector2 position = transform.position;

        // horizontal screen wrapping
        if (position.x + radius > ScreenUtils.ScreenRight)
        {
            position.x *= -1;
        }
        else if (position.x + radius < ScreenUtils.ScreenLeft)
        {
            position.x *= -1;
        }

        // vertical screen wrapping
        if (position.y + radius > ScreenUtils.ScreenBottom)
        {
            position.y *= -1;
        }
        else if (position.y + radius < ScreenUtils.ScreenTop)
        {
            position.y *= -1;
        }
        transform.position = position;
    }
}
