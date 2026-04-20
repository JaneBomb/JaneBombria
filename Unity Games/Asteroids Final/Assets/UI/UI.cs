using UnityEngine;
using UnityEngine.SceneManagement;
/// <summary>
/// Handles the UI.
/// Including buttons and game over screen
/// </summary>
public class UI : MonoBehaviour
{

    /// <summary>
    /// Start button. Loads game scene.
    /// </summary>
    public void StartButton()
    {
        SceneManager.LoadScene("Scene0");
    }

    /// <summary>
    /// Quit button. Quits the game.
    /// </summary>
    public void QuitButton()
    {
        Application.Quit();
    }

}
