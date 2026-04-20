using UnityEngine;
using UnityEngine.SceneManagement;
using TMPro;
using System.Security.Cryptography.X509Certificates;
using System.Net;

/// <summary>
/// Gameover screen and restart button
/// </summary>
public class GameOver : MonoBehaviour
{
    [SerializeField]
    private Canvas gameOverCanvas;

    public static GameOver Instance;

    void Awake()
    {
        // creates a singleton
        if (Instance != null && Instance != this)
        {
            // Destroys duplicates
            Destroy(gameObject);
        }
        else
        {
            Instance = this;
        }
        Time.timeScale = 1f;
        gameOverCanvas.enabled = false;
    }
    /// <summary>
    /// Restart button. Reloads game scene.
    /// </summary>
    public void RestartButton()
    {
        SceneManager.LoadScene("Scene0");
    }

    ///
    /// Quit button
    /// 
    public void Quit()
    {
        Application.Quit();
    }

    /// <summary>
    /// Game over UI
    /// </summary>
    public void GameOverScreen()
    {
        Time.timeScale = 0f;
        gameOverCanvas.enabled = true;
    }
}
