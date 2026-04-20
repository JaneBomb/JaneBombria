using UnityEngine;
using TMPro;

/// <summary>
/// Counts how many seconds survived
/// </summary>
public class HUD : MonoBehaviour
{
    [SerializeField]
    private TextMeshProUGUI TextMeshProUGUI;
    bool currentlyPlaying = true;
    float elapsedTime = 0;

    /// <summary>
    /// Start is called before the first frame update
    /// </summary>
    void Start()
    {
        TextMeshProUGUI.text = "0";
    }

    /// <summary>
    /// Update is called once per frame
    /// Counts timer up
    /// </summary>
    void Update()
    {
        if (currentlyPlaying == true)
        {
            elapsedTime = elapsedTime + Time.deltaTime;
            TextMeshProUGUI.text = ((int)elapsedTime).ToString();
        }
    }

    /// <summary>
    /// Stops timer
    /// </summary>
    public void StopGameTimer()
    {
        currentlyPlaying = false;
    }
}

